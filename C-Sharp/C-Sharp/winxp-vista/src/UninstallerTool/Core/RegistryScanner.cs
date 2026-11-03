using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using Microsoft.Win32;
using UninstallerTool.Infrastructure;
using UninstallerTool.Models;

namespace UninstallerTool.Core
{
    internal static class RegistryScanner
    {
        internal sealed class UninstallBase
        {
            public UninstallBase(RegistryHive hive, RegistryView view, string hiveName, string path)
            {
                Hive = hive;
                View = view;
                HiveName = hiveName;
                Path = path;
            }

            public RegistryHive Hive { get; }

            public RegistryView View { get; }

            public string HiveName { get; }

            public string Path { get; }
        }

        public static readonly UninstallBase[] UninstallBases =
        {
            new UninstallBase(
                RegistryHive.LocalMachine,
                RegistryView.Registry64,
                "HKEY_LOCAL_MACHINE",
                @"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            new UninstallBase(
                RegistryHive.LocalMachine,
                RegistryView.Registry64,
                "HKEY_LOCAL_MACHINE",
                @"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            new UninstallBase(
                RegistryHive.CurrentUser,
                RegistryView.Default,
                "HKEY_CURRENT_USER",
                @"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
        };

        public static IList<ProgramEntry> ScanInstalledPrograms()
        {
            var programs = new Dictionary<string, ProgramEntry>(StringComparer.Ordinal);

            foreach (var root in UninstallBases)
            {
                try
                {
                    using (var baseKey = RegistryKey.OpenBaseKey(root.Hive, root.View)
                               .OpenSubKey(root.Path))
                    {
                        if (baseKey == null)
                        {
                            continue;
                        }

                        foreach (var subKeyName in baseKey.GetSubKeyNames())
                        {
                            ProgramEntry program;
                            try
                            {
                                using (var subKey = baseKey.OpenSubKey(subKeyName))
                                {
                                    program = ReadProgram(subKey, root, subKeyName);
                                }
                            }
                            catch (IOException)
                            {
                                continue;
                            }
                            catch (UnauthorizedAccessException)
                            {
                                continue;
                            }
                            catch (System.Security.SecurityException)
                            {
                                continue;
                            }

                            if (program == null)
                            {
                                continue;
                            }

                            var identity = string.Join(
                                "|",
                                program.Name.ToLowerInvariant(),
                                program.Version.ToLowerInvariant(),
                                program.UninstallString.ToLowerInvariant());

                            if (!programs.ContainsKey(identity))
                            {
                                programs[identity] = program;
                            }
                        }
                    }
                }
                catch (IOException)
                {
                }
                catch (UnauthorizedAccessException)
                {
                }
                catch (System.Security.SecurityException)
                {
                }
            }

            return programs.Values
                .OrderBy(item => item.Name, StringComparer.OrdinalIgnoreCase)
                .ToList();
        }

        private static ProgramEntry ReadProgram(RegistryKey key, UninstallBase root, string subKeyName)
        {
            if (key == null)
            {
                return null;
            }

            var name = ReadString(key, "DisplayName");
            var uninstall = ReadString(key, "UninstallString");
            var quiet = ReadString(key, "QuietUninstallString");
            var command = uninstall.Length > 0 ? uninstall : quiet;

            if (name.Length == 0 || command.Length == 0 || ReadSystemComponent(key))
            {
                return null;
            }

            var icon = ReadString(key, "DisplayIcon");
            var location = CleanLocation(ReadString(key, "InstallLocation"));
            if (location.Length == 0)
            {
                location = CleanLocation(IconDirectory(icon));
            }

            return new ProgramEntry
            {
                Name = name,
                UninstallString = Environment.ExpandEnvironmentVariables(uninstall),
                QuietUninstallString = Environment.ExpandEnvironmentVariables(quiet),
                InstallLocation = location,
                Publisher = ReadString(key, "Publisher"),
                InstallDate = ReadString(key, "InstallDate"),
                Version = ReadString(key, "DisplayVersion"),
                SizeKb = ReadSize(key),
                Icon = Environment.ExpandEnvironmentVariables(icon),
                Source = ProgramSource.Registry,
                RegistryHive = root.HiveName,
                RegistrySubkey = root.Path + "\\" + subKeyName
            };
        }

        private static string ReadString(RegistryKey key, string name)
        {
            try
            {
                var value = key.GetValue(name);
                return value == null ? string.Empty : value.ToString().Trim();
            }
            catch (IOException)
            {
                return string.Empty;
            }
            catch (UnauthorizedAccessException)
            {
                return string.Empty;
            }
            catch (System.Security.SecurityException)
            {
                return string.Empty;
            }
        }

        private static long ReadSize(RegistryKey key)
        {
            try
            {
                var value = key.GetValue("EstimatedSize");
                if (value == null)
                {
                    return 0;
                }

                if (value is int number)
                {
                    return Math.Max(0, number);
                }

                return double.TryParse(
                    value.ToString(),
                    NumberStyles.Float,
                    CultureInfo.InvariantCulture,
                    out var parsed)
                    ? (long)Math.Max(0, parsed)
                    : 0;
            }
            catch (IOException)
            {
                return 0;
            }
            catch (UnauthorizedAccessException)
            {
                return 0;
            }
            catch (System.Security.SecurityException)
            {
                return 0;
            }
        }

        private static bool ReadSystemComponent(RegistryKey key)
        {
            var value = ReadString(key, "SystemComponent");
            return value == "1";
        }

        private static string IconDirectory(string displayIcon)
        {
            var reference = Formatting.SplitIconReference(displayIcon);
            return Formatting.IsFile(reference.Path) ? Path.GetDirectoryName(reference.Path) ?? string.Empty : string.Empty;
        }

        public static string CleanLocation(string value)
        {
            var text = Safety.ExpandPath(value);
            if (text.Length == 0)
            {
                return string.Empty;
            }

            var trimmed = Safety.AbsolutePath(text);
            if (trimmed.Length == 0)
            {
                return string.Empty;
            }

            return trimmed;
        }
    }
}
