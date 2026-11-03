using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using Microsoft.Win32;
using UninstallerTool.Infrastructure;
using UninstallerTool.Models;

namespace UninstallerTool.Core
{
    internal sealed class RegistrySnapshot
    {
        private static readonly HashSet<string> ReservedSoftwareKeys = new HashSet<string>(StringComparer.Ordinal)
        {
            "classes",
            "clients",
            "microsoft",
            "policies",
            "registeredapplications",
            "windows",
            "wow6432node",
            "uninstall",
            "microsoftoffice",
            "office"
        };

        private static readonly (RegistryHive Hive, RegistryView View, string HiveName, string Path)[] SoftwareBases =
        {
            (RegistryHive.LocalMachine, RegistryView.Registry64, "HKEY_LOCAL_MACHINE", @"SOFTWARE"),
            (RegistryHive.LocalMachine, RegistryView.Registry64, "HKEY_LOCAL_MACHINE", @"SOFTWARE\WOW6432Node"),
            (RegistryHive.CurrentUser, RegistryView.Default, "HKEY_CURRENT_USER", @"SOFTWARE")
        };

        private static readonly Dictionary<string, RegistryHive> Hives =
            new Dictionary<string, RegistryHive>(StringComparer.Ordinal)
            {
                { "HKEY_LOCAL_MACHINE", RegistryHive.LocalMachine },
                { "HKEY_CURRENT_USER", RegistryHive.CurrentUser }
            };

        private readonly Dictionary<string, List<RegistryEntry>> _byKeyName =
            new Dictionary<string, List<RegistryEntry>>(StringComparer.Ordinal);

        private readonly Dictionary<string, List<RegistryEntry>> _byDisplayName =
            new Dictionary<string, List<RegistryEntry>>(StringComparer.Ordinal);

        public RegistrySnapshot(IEnumerable<RegistryEntry> entries)
        {
            Entries = (entries ?? Enumerable.Empty<RegistryEntry>()).ToList();
            foreach (var entry in Entries)
            {
                Add(_byKeyName, Formatting.NormalizeName(entry.KeyName), entry);
                if (entry.DisplayName.Length > 0)
                {
                    Add(_byDisplayName, Formatting.NormalizeName(entry.DisplayName), entry);
                }
            }
        }

        public List<RegistryEntry> Entries { get; }

        public static RegistrySnapshot Build()
        {
            var entries = new List<RegistryEntry>();

            foreach (var root in RegistryScanner.UninstallBases)
            {
                foreach (var (keyName, displayName) in EnumerateSubKeys(root.Hive, root.View, root.Path))
                {
                    entries.Add(new RegistryEntry(
                        root.HiveName,
                        root.Path + "\\" + keyName,
                        displayName,
                        keyName,
                        RegistryEntryKind.Uninstall));
                }
            }

            foreach (var (hive, view, hiveName, basePath) in SoftwareBases)
            {
                foreach (var vendorName in EnumerateKeyNames(hive, view, basePath))
                {
                    if (ReservedSoftwareKeys.Contains(Formatting.NormalizeName(vendorName)))
                    {
                        continue;
                    }

                    var vendorPath = basePath + "\\" + vendorName;
                    foreach (var productName in EnumerateKeyNames(hive, view, vendorPath))
                    {
                        if (ReservedSoftwareKeys.Contains(Formatting.NormalizeName(productName)))
                        {
                            continue;
                        }

                        entries.Add(new RegistryEntry(
                            hiveName,
                            vendorPath + "\\" + productName,
                            string.Empty,
                            productName,
                            RegistryEntryKind.Vendor));
                    }
                }
            }

            Log.Info("Registry snapshot contains " + entries.Count.ToString(CultureInfo.InvariantCulture) + " entries");
            return new RegistrySnapshot(entries);
        }

        public List<RegistryEntry> Find(string name, string publisher)
        {
            var normalizedName = Formatting.NormalizeName(name);
            var normalizedPublisher = Formatting.NormalizeName(publisher);
            var matches = new List<RegistryEntry>();
            var seen = new HashSet<string>(StringComparer.Ordinal);

            if (normalizedName.Length == 0)
            {
                return matches;
            }

            void Add(RegistryEntry entry)
            {
                var key = entry.Path.ToLowerInvariant();
                if (seen.Add(key))
                {
                    matches.Add(entry);
                }
            }

            if (_byDisplayName.TryGetValue(normalizedName, out var byDisplay))
            {
                foreach (var entry in byDisplay.Where(item => item.Kind == RegistryEntryKind.Uninstall))
                {
                    Add(entry);
                }
            }

            if (_byKeyName.TryGetValue(normalizedName, out var byKey))
            {
                foreach (var entry in byKey)
                {
                    if (entry.Kind == RegistryEntryKind.Vendor && normalizedPublisher.Length > 0)
                    {
                        if (string.Equals(VendorFromSubKey(entry.Subkey), normalizedPublisher, StringComparison.Ordinal))
                        {
                            Add(entry);
                        }
                    }
                    else if (entry.Kind == RegistryEntryKind.Uninstall && entry.DisplayName.Length == 0)
                    {
                        Add(entry);
                    }
                }
            }

            return matches;
        }

        public static bool IsSafeEntry(RegistryEntry entry)
        {
            if (entry == null || !Hives.ContainsKey(entry.Hive))
            {
                return false;
            }

            var subkey = entry.Subkey;
            if (string.IsNullOrWhiteSpace(subkey) || subkey.Contains("*") || subkey.Contains("?"))
            {
                return false;
            }

            if (entry.Kind == RegistryEntryKind.Uninstall)
            {
                foreach (var root in RegistryScanner.UninstallBases)
                {
                    var prefix = root.Path + "\\";
                    if (!subkey.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }

                    var remainder = subkey.Substring(prefix.Length);
                    return remainder.Length > 0 && remainder.IndexOf('\\') < 0;
                }

                return false;
            }

            var parts = SplitSubKey(subkey);
            if (parts.Count == 0 || Formatting.NormalizeName(parts[0]) != "software")
            {
                return false;
            }

            string vendor;
            string product;
            if (parts.Count == 3)
            {
                vendor = parts[1];
                product = parts[2];
            }
            else if (parts.Count == 4 && Formatting.NormalizeName(parts[1]) == "wow6432node")
            {
                vendor = parts[2];
                product = parts[3];
            }
            else
            {
                return false;
            }

            if (ReservedSoftwareKeys.Contains(Formatting.NormalizeName(vendor)) ||
                ReservedSoftwareKeys.Contains(Formatting.NormalizeName(product)))
            {
                return false;
            }

            return vendor.Length > 0 && product.Length > 0;
        }

        public static string ExportKey(RegistryEntry entry, string directory)
        {
            if (!IsSafeEntry(entry))
            {
                throw new IOException("Refusing to export an unsafe registry key: " + entry.Path);
            }

            Directory.CreateDirectory(directory);
            var timestamp = DateTime.Now.ToString("yyyyMMdd-HHmmss", CultureInfo.InvariantCulture);
            var safeName = new string(entry.Path
                .Select(character => char.IsLetterOrDigit(character) || character == '.' || character == '_' || character == '-'
                    ? character
                    : '_')
                .ToArray()).Trim('_');

            if (safeName.Length > 120)
            {
                safeName = safeName.Substring(0, 120);
            }

            var target = Path.Combine(directory, safeName + "-" + timestamp + ".reg");
            var hive = Hives[entry.Hive];
            using (var baseKey = RegistryKey.OpenBaseKey(hive, RegistryView.Default))
            using (var key = baseKey.OpenSubKey(entry.Subkey))
            {
                if (key == null)
                {
                    throw new IOException("The registry key no longer exists: " + entry.Path);
                }

                var builder = new StringBuilder();
                builder.AppendLine("Windows Registry Editor Version 5.00");
                builder.AppendLine();
                WriteKey(builder, key, entry.Hive + "\\" + entry.Subkey);
                File.WriteAllText(target, builder.ToString(), Encoding.Unicode);
            }

            if (!File.Exists(target) || new FileInfo(target).Length == 0)
            {
                throw new IOException("Could not export " + entry.Path);
            }

            Log.Info("Exported registry backup: " + target);
            return target;
        }

        public static void DeleteEntry(RegistryEntry entry)
        {
            if (!IsSafeEntry(entry))
            {
                throw new IOException("Refusing to delete an unsafe registry key: " + entry.Path);
            }

            var hive = Hives[entry.Hive];
            using (var baseKey = RegistryKey.OpenBaseKey(hive, RegistryView.Default))
            {
                DeleteTree(baseKey, entry.Subkey);
            }

            Log.Info("Deleted registry key: " + entry.Path);
        }

        private static void WriteKey(StringBuilder builder, RegistryKey key, string fullPath)
        {
            builder.Append('[').Append(fullPath).AppendLine("]");

            foreach (var name in key.GetValueNames())
            {
                WriteValue(builder, key, name);
            }

            builder.AppendLine();

            foreach (var child in key.GetSubKeyNames())
            {
                using (var subKey = key.OpenSubKey(child))
                {
                    if (subKey != null)
                    {
                        WriteKey(builder, subKey, fullPath + "\\" + child);
                    }
                }
            }
        }

        private static void WriteValue(StringBuilder builder, RegistryKey key, string name)
        {
            object value;
            RegistryValueKind kind;
            try
            {
                value = key.GetValue(name, null, RegistryValueOptions.DoNotExpandEnvironmentNames);
                kind = key.GetValueKind(name);
            }
            catch (IOException)
            {
                return;
            }
            catch (UnauthorizedAccessException)
            {
                return;
            }
            catch (System.Security.SecurityException)
            {
                return;
            }

            if (value == null)
            {
                return;
            }

            string encoded;
            switch (kind)
            {
                case RegistryValueKind.String:
                    encoded = EncodeString(value.ToString(), 1);
                    break;
                case RegistryValueKind.ExpandString:
                    encoded = EncodeString(value.ToString(), 2);
                    break;
                case RegistryValueKind.MultiString:
                    encoded = EncodeMultiString(value as string[]);
                    break;
                case RegistryValueKind.Binary:
                    encoded = EncodeBytes(value as byte[], "hex:");
                    break;
                case RegistryValueKind.DWord:
                    encoded = "dword:" + unchecked((uint)Convert.ToInt32(value, CultureInfo.InvariantCulture)).ToString("x8", CultureInfo.InvariantCulture);
                    break;
                case RegistryValueKind.QWord:
                    encoded = EncodeBytes(BitConverter.GetBytes(Convert.ToInt64(value, CultureInfo.InvariantCulture)), "hex(b):");
                    break;
                default:
                    return;
            }

            builder.Append(FormatValueName(name)).Append('=').AppendLine(encoded);
        }

        private static string EncodeString(string text, int kind)
        {
            var value = text ?? string.Empty;
            if (kind == 1 && value.IndexOfAny(new[] { '\0', '\r', '\n' }) < 0)
            {
                return QuoteValue(value);
            }

            return EncodeBytes(Encoding.Unicode.GetBytes(value + "\0"), "hex(" + kind.ToString(CultureInfo.InvariantCulture) + "):");
        }

        private static string EncodeMultiString(string[] values)
        {
            var items = values ?? new string[0];
            var text = string.Join("\0", items) + "\0\0";
            return EncodeBytes(Encoding.Unicode.GetBytes(text), "hex(7):");
        }

        private static string EncodeBytes(byte[] bytes, string prefix)
        {
            if (bytes == null || bytes.Length == 0)
            {
                return prefix;
            }

            return prefix + string.Join(",", bytes.Select(item => item.ToString("x2", CultureInfo.InvariantCulture)));
        }

        private static string QuoteValue(string text)
        {
            return "\"" + text.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
        }

        private static string FormatValueName(string name)
        {
            if (string.IsNullOrEmpty(name))
            {
                return "@";
            }

            return QuoteValue(name);
        }

        private static void DeleteTree(RegistryKey parent, string path)
        {
            using (var key = parent.OpenSubKey(path, true))
            {
                if (key == null)
                {
                    return;
                }

                foreach (var child in key.GetSubKeyNames())
                {
                    DeleteTree(key, child);
                }
            }

            parent.DeleteSubKey(path, false);
        }

        private static void Add(Dictionary<string, List<RegistryEntry>> map, string key, RegistryEntry entry)
        {
            if (!map.TryGetValue(key, out var items))
            {
                items = new List<RegistryEntry>();
                map[key] = items;
            }

            items.Add(entry);
        }

        private static List<string> SplitSubKey(string subkey)
        {
            return subkey.Split(new[] { '\\' }, StringSplitOptions.RemoveEmptyEntries).ToList();
        }

        private static string VendorFromSubKey(string subkey)
        {
            var parts = SplitSubKey(subkey);
            if (parts.Count == 3)
            {
                return Formatting.NormalizeName(parts[1]);
            }

            if (parts.Count == 4 && Formatting.NormalizeName(parts[1]) == "wow6432node")
            {
                return Formatting.NormalizeName(parts[2]);
            }

            return string.Empty;
        }

        private static IEnumerable<string> EnumerateKeyNames(RegistryHive hive, RegistryView view, string path)
        {
            RegistryKey key;
            try
            {
                key = RegistryKey.OpenBaseKey(hive, view).OpenSubKey(path);
            }
            catch (IOException)
            {
                yield break;
            }
            catch (UnauthorizedAccessException)
            {
                yield break;
            }
            catch (System.Security.SecurityException)
            {
                yield break;
            }

            if (key == null)
            {
                yield break;
            }

            string[] names;
            using (key)
            {
                try
                {
                    names = key.GetSubKeyNames();
                }
                catch (IOException)
                {
                    yield break;
                }
                catch (UnauthorizedAccessException)
                {
                    yield break;
                }
            }

            foreach (var name in names)
            {
                yield return name;
            }
        }

        private static IEnumerable<(string KeyName, string DisplayName)> EnumerateSubKeys(
            RegistryHive hive,
            RegistryView view,
            string path)
        {
            foreach (var subkey in EnumerateKeyNames(hive, view, path))
            {
                var displayName = string.Empty;
                try
                {
                    using (var key = RegistryKey.OpenBaseKey(hive, view).OpenSubKey(path + "\\" + subkey))
                    {
                        var value = key?.GetValue("DisplayName");
                        displayName = value?.ToString().Trim() ?? string.Empty;
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

                yield return (subkey, displayName);
            }
        }
    }
}
