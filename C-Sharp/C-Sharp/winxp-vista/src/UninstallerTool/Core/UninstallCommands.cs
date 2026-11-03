using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;

namespace UninstallerTool.Core
{
    internal static class UninstallCommands
    {
        private static readonly HashSet<int> MsiSuccessCodes = new HashSet<int> { 0, 1641, 3010 };

        private static readonly HashSet<int> MsiRebootCodes = new HashSet<int> { 1641, 3010 };

        private static readonly string[] SilentFallbackFlags = { "/S", "/s", "/silent", "/quiet", "-s", "--silent" };

        private static readonly string[] NsisFlags = { "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART" };

        private static readonly HashSet<string> BatchExtensions = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            ".bat",
            ".cmd"
        };

        private static readonly Regex GuidOnly = new Regex(@"^\{[0-9A-Fa-f-]+\}$", RegexOptions.Compiled);

        private static readonly Regex ExecutableEnding = new Regex(@"(?<exe>.+?\.(?:exe|com|bat|cmd))(?=\s|$)", RegexOptions.IgnoreCase | RegexOptions.Compiled);

        private static readonly Regex MsiInstallSwitch = new Regex(@"^/i(.+)$", RegexOptions.IgnoreCase | RegexOptions.Compiled);

        public static string SystemRoot()
        {
            var root = Environment.GetEnvironmentVariable("SYSTEMROOT") ??
                       Environment.GetEnvironmentVariable("WINDIR") ?? @"C:\Windows";
            return root;
        }

        public static string System32Directory()
        {
            return Path.Combine(SystemRoot(), "System32");
        }

        public static string PowerShellPath()
        {
            var candidate = Path.Combine(System32Directory(), "WindowsPowerShell", "v1.0", "powershell.exe");
            return File.Exists(candidate) ? candidate : "powershell.exe";
        }

        public static string CmdPath()
        {
            var candidate = Path.Combine(System32Directory(), "cmd.exe");
            return File.Exists(candidate) ? candidate : "cmd.exe";
        }

        public static string MsiexecPath()
        {
            var candidate = Path.Combine(System32Directory(), "msiexec.exe");
            return File.Exists(candidate) ? candidate : "msiexec.exe";
        }

        public static List<string> SplitWindowsCommand(string command)
        {
            var text = Environment.ExpandEnvironmentVariables(command ?? string.Empty).Trim();
            if (text.Length == 0)
            {
                return new List<string>();
            }

            if (GuidOnly.IsMatch(text))
            {
                return new List<string> { MsiexecPath(), "/x", text };
            }

            string executable;
            string remainder;
            if (text[0] == '"')
            {
                var end = text.IndexOf('"', 1);
                if (end < 0)
                {
                    return new List<string>();
                }

                executable = text.Substring(1, end - 1);
                remainder = text.Substring(end + 1).Trim();
            }
            else
            {
                var match = ExecutableEnding.Match(text);
                if (match.Success)
                {
                    executable = match.Groups["exe"].Value;
                    remainder = text.Substring(match.Index + match.Length).Trim();
                }
                else
                {
                    var separator = text.IndexOf(' ');
                    if (separator < 0)
                    {
                        executable = text;
                        remainder = string.Empty;
                    }
                    else
                    {
                        executable = text.Substring(0, separator);
                        remainder = text.Substring(separator + 1).Trim();
                    }
                }
            }

            var result = new List<string> { executable };
            result.AddRange(SplitArguments(remainder));
            return result;
        }

        public static List<string> SplitArguments(string arguments)
        {
            var tokens = new List<string>();
            if (string.IsNullOrEmpty(arguments))
            {
                return tokens;
            }

            var current = new System.Text.StringBuilder();
            var quoted = false;
            foreach (var character in arguments)
            {
                if (character == '"')
                {
                    quoted = !quoted;
                }
                else if (char.IsWhiteSpace(character) && !quoted)
                {
                    if (current.Length > 0)
                    {
                        tokens.Add(current.ToString());
                        current.Clear();
                    }
                }
                else
                {
                    current.Append(character);
                }
            }

            if (current.Length > 0)
            {
                tokens.Add(current.ToString());
            }

            return tokens;
        }

        public static bool IsMsiCommand(IList<string> arguments)
        {
            if (arguments == null || arguments.Count == 0)
            {
                return false;
            }

            var name = Path.GetFileName(arguments[0]).ToLowerInvariant();
            return name == "msiexec" || name == "msiexec.exe";
        }

        public static List<string> BuildUninstallCommand(string uninstallString, bool silent)
        {
            var arguments = SplitWindowsCommand(uninstallString);
            if (arguments.Count == 0)
            {
                return arguments;
            }

            if (IsMsiCommand(arguments))
            {
                return BuildMsiCommand(arguments, silent);
            }

            var extension = Path.GetExtension(arguments[0]) ?? string.Empty;
            if (silent && !BatchExtensions.Contains(extension))
            {
                var existing = new HashSet<string>(
                    arguments.Skip(1).Select(item => item.ToLowerInvariant()),
                    StringComparer.OrdinalIgnoreCase);
                var executable = Path.GetFileName(arguments[0]).ToLowerInvariant();
                if (executable.Contains("unins"))
                {
                    foreach (var flag in NsisFlags)
                    {
                        if (!existing.Contains(flag.ToLowerInvariant()))
                        {
                            arguments.Add(flag);
                        }
                    }
                }
                else if (!existing.Overlaps(SilentFallbackFlags.Select(item => item.ToLowerInvariant())))
                {
                    arguments.Add("/S");
                }
            }

            return arguments;
        }

        public static string ResolveExecutable(string name)
        {
            var text = Environment.ExpandEnvironmentVariables((name ?? string.Empty).Trim()).Trim('"');
            if (text.Length == 0)
            {
                return string.Empty;
            }

            if (File.Exists(text))
            {
                return Path.GetFullPath(text);
            }

            var baseName = Path.GetFileName(text).ToLowerInvariant();
            switch (baseName)
            {
                case "powershell":
                case "powershell.exe":
                    if (File.Exists(PowerShellPath()))
                    {
                        return PowerShellPath();
                    }

                    break;
                case "cmd":
                case "cmd.exe":
                    if (File.Exists(CmdPath()))
                    {
                        return CmdPath();
                    }

                    break;
                case "msiexec":
                case "msiexec.exe":
                    if (File.Exists(MsiexecPath()))
                    {
                        return MsiexecPath();
                    }

                    break;
            }

            foreach (var directory in SearchDirectories())
            {
                var candidate = Path.Combine(directory, baseName);
                if (File.Exists(candidate))
                {
                    return Path.GetFullPath(candidate);
                }
            }

            var pathVariable = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
            foreach (var directory in pathVariable.Split(new[] { ';' }, StringSplitOptions.RemoveEmptyEntries))
            {
                try
                {
                    var candidate = Path.Combine(directory.Trim().Trim('"'), baseName);
                    if (File.Exists(candidate))
                    {
                        return Path.GetFullPath(candidate);
                    }
                }
                catch (ArgumentException)
                {
                }
            }

            return string.Empty;
        }

        public static bool CommandExists(IList<string> arguments)
        {
            return arguments != null && arguments.Count > 0 && ResolveExecutable(arguments[0]).Length > 0;
        }

        public static List<string> PrepareProcessArguments(IList<string> arguments)
        {
            if (arguments == null || arguments.Count == 0)
            {
                throw new ArgumentException("Empty command", nameof(arguments));
            }

            var executable = ResolveExecutable(arguments[0]);
            if (executable.Length == 0)
            {
                throw new FileNotFoundException(arguments[0]);
            }

            var prepared = new List<string> { executable };
            prepared.AddRange(arguments.Skip(1));

            if (BatchExtensions.Contains(Path.GetExtension(executable) ?? string.Empty))
            {
                return new List<string> { CmdPath(), "/d", "/s", "/c", QuoteCommandLine(prepared) };
            }

            return prepared;
        }

        public static bool ExitCodeSucceeded(IList<string> arguments, int code)
        {
            return SuccessExitCodes(arguments).Contains(code);
        }

        public static HashSet<int> SuccessExitCodes(IList<string> arguments)
        {
            return IsMsiCommand(arguments) ? MsiSuccessCodes : new HashSet<int> { 0 };
        }

        public static bool IsRebootCode(int code)
        {
            return MsiRebootCodes.Contains(code);
        }

        public static string QuoteCommandLine(IEnumerable<string> arguments)
        {
            return string.Join(" ", arguments.Select(QuoteArgument));
        }

        private static List<string> BuildMsiCommand(List<string> arguments, bool silent)
        {
            var normalized = new List<string> { arguments[0] };
            var actionFound = false;
            foreach (var argument in arguments.Skip(1))
            {
                var installSwitch = MsiInstallSwitch.Match(argument);
                if (installSwitch.Success)
                {
                    normalized.Add("/x");
                    normalized.Add(installSwitch.Groups[1].Value);
                    actionFound = true;
                }
                else if (string.Equals(argument, "/i", StringComparison.OrdinalIgnoreCase))
                {
                    normalized.Add("/x");
                    actionFound = true;
                }
                else
                {
                    normalized.Add(argument);
                    var lowered = argument.ToLowerInvariant();
                    if (lowered == "/x" || lowered.StartsWith("/x{", StringComparison.Ordinal))
                    {
                        actionFound = true;
                    }
                }
            }

            if (!actionFound)
            {
                normalized.Insert(1, "/x");
            }

            if (silent)
            {
                var existing = new HashSet<string>(normalized.Select(item => item.ToLowerInvariant()));
                if (!existing.Contains("/quiet") && !existing.Contains("/qn") && !existing.Contains("/passive"))
                {
                    normalized.Add("/quiet");
                }

                if (!existing.Contains("/norestart"))
                {
                    normalized.Add("/norestart");
                }
            }

            return normalized;
        }

        private static string[] SearchDirectories()
        {
            var candidates = new[]
            {
                System32Directory(),
                Path.Combine(SystemRoot(), "SysWOW64"),
                SystemRoot(),
                Environment.GetEnvironmentVariable("LOCALAPPDATA") ?? string.Empty
            };

            return candidates.Where(item => !string.IsNullOrWhiteSpace(item)).ToArray();
        }

        private static string QuoteArgument(string value)
        {
            if (string.IsNullOrEmpty(value))
            {
                return "\"\"";
            }

            return value.IndexOfAny(new[] { ' ', '\t' }) >= 0 ? "\"" + value + "\"" : value;
        }
    }
}
