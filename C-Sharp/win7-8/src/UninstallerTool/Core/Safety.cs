using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;

namespace UninstallerTool.Core
{
    internal static class Safety
    {
        private static readonly Regex DriveOnly = new Regex(@"^[A-Za-z]:$", RegexOptions.Compiled);

        private static readonly Lazy<string[]> ProgramRootDirectories = new Lazy<string[]>(BuildProgramRoots);

        private static readonly Lazy<string[]> ExtraRootDirectories = new Lazy<string[]>(BuildExtraRoots);

        private static readonly Lazy<string[]> ProtectedRootDirectories = new Lazy<string[]>(BuildProtectedDirectories);

        public static string ExpandPath(string value)
        {
            var text = (value ?? string.Empty).Trim().Trim('"').Trim();
            if (text.Length == 0)
            {
                return string.Empty;
            }

            text = Environment.ExpandEnvironmentVariables(text);
            if (DriveOnly.IsMatch(text))
            {
                text += Path.DirectorySeparatorChar;
            }

            return text;
        }

        public static string NormalizePath(string value)
        {
            var text = ExpandPath(value);
            if (text.Length == 0)
            {
                return string.Empty;
            }

            try
            {
                return TrimTrailing(Path.GetFullPath(text)).ToLowerInvariant();
            }
            catch (ArgumentException)
            {
                return string.Empty;
            }
            catch (NotSupportedException)
            {
                return string.Empty;
            }
            catch (PathTooLongException)
            {
                return string.Empty;
            }
        }

        public static string AbsolutePath(string value)
        {
            var text = ExpandPath(value);
            if (text.Length == 0)
            {
                return string.Empty;
            }

            try
            {
                return TrimTrailing(Path.GetFullPath(text));
            }
            catch (ArgumentException)
            {
                return string.Empty;
            }
            catch (NotSupportedException)
            {
                return string.Empty;
            }
            catch (PathTooLongException)
            {
                return string.Empty;
            }
        }

        public static int PathDepth(string path)
        {
            var normalized = NormalizePath(path);
            if (normalized.Length == 0)
            {
                return 0;
            }

            var root = Path.GetPathRoot(normalized) ?? string.Empty;
            var tail = normalized.Substring(root.Length);
            return tail.Split(new[] { Path.DirectorySeparatorChar }, StringSplitOptions.RemoveEmptyEntries).Length;
        }

        public static bool IsWithin(string path, string root)
        {
            var child = NormalizePath(path);
            var parent = NormalizePath(root);
            if (child.Length == 0 || parent.Length == 0)
            {
                return false;
            }

            if (string.Equals(child, parent, StringComparison.Ordinal))
            {
                return true;
            }

            return child.StartsWith(parent + Path.DirectorySeparatorChar, StringComparison.Ordinal);
        }

        public static bool IsReparsePoint(string path)
        {
            if (string.IsNullOrEmpty(path))
            {
                return false;
            }

            try
            {
                var attributes = File.GetAttributes(path);
                return (attributes & FileAttributes.ReparsePoint) == FileAttributes.ReparsePoint;
            }
            catch (IOException)
            {
                return false;
            }
            catch (UnauthorizedAccessException)
            {
                return false;
            }
            catch (ArgumentException)
            {
                return false;
            }
        }

        public static bool HasReparseComponent(string path)
        {
            var current = NormalizePath(path);
            if (current.Length == 0)
            {
                return false;
            }

            var root = Path.GetPathRoot(current) ?? string.Empty;
            while (current.Length > 0 && !string.Equals(current, root, StringComparison.Ordinal))
            {
                if (IsReparsePoint(current))
                {
                    return true;
                }

                var parent = Path.GetDirectoryName(current);
                if (string.IsNullOrEmpty(parent) || string.Equals(parent, current, StringComparison.Ordinal))
                {
                    break;
                }

                current = parent;
            }

            return false;
        }

        public static string WindowsDirectory()
        {
            var root = Environment.GetEnvironmentVariable("SYSTEMROOT") ??
                       Environment.GetEnvironmentVariable("WINDIR") ??
                       @"C:\Windows";
            return NormalizePath(root);
        }

        public static string[] ProgramRoots()
        {
            return ProgramRootDirectories.Value;
        }

        public static string[] ExtraRoots()
        {
            return ExtraRootDirectories.Value;
        }

        public static string[] ProtectedDirectories()
        {
            return ProtectedRootDirectories.Value;
        }

        public static bool IsSafeProgramDirectory(string path)
        {
            var candidate = NormalizePath(path);
            if (candidate.Length == 0 || !SafeDirectoryExists(candidate))
            {
                return false;
            }

            var root = Path.GetPathRoot(candidate) ?? string.Empty;
            if (root.Length == 0 || candidate.Substring(root.Length).Trim('\\', '/').Length == 0)
            {
                return false;
            }

            if (PathDepth(candidate) < 2)
            {
                return false;
            }

            if (IsReparsePoint(candidate) || HasReparseComponent(candidate))
            {
                return false;
            }

            foreach (var protectedDirectory in ProtectedDirectories())
            {
                if (string.Equals(candidate, protectedDirectory, StringComparison.Ordinal))
                {
                    return false;
                }

                if (IsWithin(protectedDirectory, candidate))
                {
                    return false;
                }
            }

            if (IsWithin(candidate, WindowsDirectory()))
            {
                return false;
            }

            return !ProgramRoots().Any(item => string.Equals(candidate, item, StringComparison.Ordinal));
        }

        public static bool IsSafeRemovalPath(string path, IEnumerable<string> allowedRoots)
        {
            var candidate = NormalizePath(path);
            if (candidate.Length == 0)
            {
                return false;
            }

            var root = Path.GetPathRoot(candidate) ?? string.Empty;
            if (root.Length == 0 || candidate.Substring(root.Length).Trim('\\', '/').Length == 0)
            {
                return false;
            }

            if (PathDepth(candidate) < 2)
            {
                return false;
            }

            if (IsWithin(candidate, WindowsDirectory()))
            {
                return false;
            }

            foreach (var protectedDirectory in ProtectedDirectories())
            {
                if (string.Equals(candidate, protectedDirectory, StringComparison.Ordinal))
                {
                    return false;
                }

                if (IsWithin(protectedDirectory, candidate))
                {
                    return false;
                }
            }

            var normalizedRoots = (allowedRoots ?? Array.Empty<string>())
                .Select(NormalizePath)
                .Where(item => item.Length > 0)
                .ToArray();

            if (!normalizedRoots.Any(item => IsWithin(candidate, item) && !string.Equals(candidate, item, StringComparison.Ordinal)))
            {
                return false;
            }

            if (IsReparsePoint(candidate))
            {
                return true;
            }

            return !HasReparseComponent(candidate);
        }

        public static string[] RemovalRoots()
        {
            var values = ProgramRoots().Concat(ExtraRoots());
            var result = new List<string>();
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var value in values)
            {
                var normalized = NormalizePath(value);
                if (normalized.Length == 0 || !seen.Add(normalized))
                {
                    continue;
                }

                result.Add(normalized);
            }

            return result.ToArray();
        }

        private static bool SafeDirectoryExists(string normalizedPath)
        {
            try
            {
                return Directory.Exists(normalizedPath);
            }
            catch (IOException)
            {
                return false;
            }
            catch (UnauthorizedAccessException)
            {
                return false;
            }
        }

        private static string TrimTrailing(string path)
        {
            var root = Path.GetPathRoot(path) ?? string.Empty;
            var trimmed = path.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            return trimmed.Length < root.Length ? root : trimmed;
        }

        private static string[] BuildProgramRoots()
        {
            var candidates = new[]
            {
                Environment.GetEnvironmentVariable("ProgramFiles"),
                Environment.GetEnvironmentVariable("ProgramFiles(x86)"),
                Path.Combine(Environment.GetEnvironmentVariable("LOCALAPPDATA") ?? string.Empty, "Programs")
            };

            return NormalizeExisting(candidates);
        }

        private static string[] BuildExtraRoots()
        {
            var appData = Environment.GetEnvironmentVariable("APPDATA") ?? string.Empty;
            var local = Environment.GetEnvironmentVariable("LOCALAPPDATA") ?? string.Empty;
            var programData = Environment.GetEnvironmentVariable("PROGRAMDATA") ?? string.Empty;
            var candidates = new[]
            {
                Environment.GetEnvironmentVariable("TEMP"),
                Environment.GetEnvironmentVariable("TMP"),
                Path.Combine(programData, "Package Cache"),
                Path.Combine(appData, @"Microsoft\Windows\Start Menu\Programs"),
                Path.Combine(programData, @"Microsoft\Windows\Start Menu\Programs"),
                Path.Combine(local, "Packages"),
                Path.Combine(local, "Temp")
            };

            return NormalizeExisting(candidates);
        }

        private static string[] BuildProtectedDirectories()
        {
            var systemDrive = Environment.GetEnvironmentVariable("SYSTEMDRIVE") ?? @"C:\";
            var windows = Environment.GetEnvironmentVariable("SYSTEMROOT") ??
                          Environment.GetEnvironmentVariable("WINDIR") ?? @"C:\Windows";
            var local = Environment.GetEnvironmentVariable("LOCALAPPDATA") ?? string.Empty;
            var roaming = Environment.GetEnvironmentVariable("APPDATA") ?? string.Empty;
            var profile = Environment.GetEnvironmentVariable("USERPROFILE") ?? string.Empty;
            var candidates = new[]
            {
                systemDrive,
                windows,
                Path.Combine(windows, "System32"),
                Path.Combine(windows, "SysWOW64"),
                Environment.GetEnvironmentVariable("ProgramFiles"),
                Environment.GetEnvironmentVariable("ProgramFiles(x86)"),
                Environment.GetEnvironmentVariable("PROGRAMDATA"),
                local,
                roaming,
                Path.Combine(local, "Temp"),
                Environment.GetEnvironmentVariable("TEMP"),
                Environment.GetEnvironmentVariable("TMP"),
                profile,
                Path.Combine(profile, "Desktop"),
                Path.Combine(profile, "Documents"),
                Path.Combine(profile, "Downloads")
            };

            var result = new List<string>();
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var candidate in candidates)
            {
                var normalized = NormalizePath(candidate);
                if (normalized.Length == 0 || !seen.Add(normalized))
                {
                    continue;
                }

                result.Add(normalized);
            }

            return result.ToArray();
        }

        private static string[] NormalizeExisting(IEnumerable<string> candidates)
        {
            var result = new List<string>();
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var candidate in candidates)
            {
                var normalized = NormalizePath(candidate);
                if (normalized.Length == 0 || !seen.Add(normalized) || !SafeDirectoryExists(normalized))
                {
                    continue;
                }

                result.Add(normalized);
            }

            return result.ToArray();
        }
    }
}
