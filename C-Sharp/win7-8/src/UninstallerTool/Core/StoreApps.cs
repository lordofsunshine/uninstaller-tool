using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Runtime.Serialization.Json;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using Microsoft.Win32;
using UninstallerTool.Infrastructure;
using UninstallerTool.Models;

namespace UninstallerTool.Core
{
    internal static class StoreApps
    {
        private const long CacheLifetimeSeconds = 12 * 60 * 60;
        private const string PackageRepository =
            @"Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\AppModel\Repository\Packages";
        private const string SystemPublisher = "cw5n1h2txyewy";

        private static readonly Regex GuidLike = new Regex(@"^[0-9a-fA-F-]{10,}$", RegexOptions.Compiled);
        private static readonly Regex PackageHash = new Regex(@"^[0-9a-fA-F-]{8,}$", RegexOptions.Compiled);
        private static readonly Regex ManifestIdentity = new Regex(@"<Identity\b[^>]*\bPublisher=""(?<value>[^""]*)""", RegexOptions.IgnoreCase | RegexOptions.Compiled);
        private static readonly Regex ManifestFramework = new Regex(@"<Framework>\s*true\s*</Framework>", RegexOptions.IgnoreCase | RegexOptions.Compiled);
        private static readonly Regex ManifestPublisher = new Regex(@"<PublisherDisplayName>(?<value>.*?)</PublisherDisplayName>", RegexOptions.IgnoreCase | RegexOptions.Compiled);
        private static readonly Regex ManifestDisplay = new Regex(@"<DisplayName>(?<value>.*?)</DisplayName>", RegexOptions.IgnoreCase | RegexOptions.Compiled);

        public static Task<List<ProgramEntry>> FetchAsync()
        {
            return Task.Run(() => FetchFromRegistry());
        }

        private static List<ProgramEntry> FetchFromRegistry()
        {
            var programs = new List<ProgramEntry>();

            try
            {
                using (var root = Registry.CurrentUser.OpenSubKey(PackageRepository))
                {
                    if (root == null)
                    {
                        return programs;
                    }

                    foreach (var fullName in root.GetSubKeyNames())
                    {
                        try
                        {
                            using (var packageKey = root.OpenSubKey(fullName))
                            {
                                var program = ReadPackage(packageKey, fullName);
                                if (program != null)
                                {
                                    programs.Add(program);
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

            return programs
                .GroupBy(item => item.PackageFullName, StringComparer.OrdinalIgnoreCase)
                .Select(group => group.First())
                .OrderBy(item => item.Name, StringComparer.OrdinalIgnoreCase)
                .ToList();
        }

        private static ProgramEntry ReadPackage(RegistryKey packageKey, string fullName)
        {
            var parts = (fullName ?? string.Empty).Split('_');
            if (parts.Length < 5 || parts[0].Length == 0 || parts[1].Length == 0)
            {
                return null;
            }

            if (parts[3].Length > 0 || string.Equals(parts[4], SystemPublisher, StringComparison.OrdinalIgnoreCase))
            {
                return null;
            }

            var installLocation = packageKey == null
                ? string.Empty
                : (packageKey.GetValue("PackageRootFolder") as string ?? string.Empty).Trim();

            var registryDisplay = packageKey == null
                ? string.Empty
                : (packageKey.GetValue("DisplayName") as string ?? string.Empty).Trim();

            var manifest = ReadManifest(installLocation);
            if (manifest != null && ManifestFramework.IsMatch(manifest))
            {
                return null;
            }

            var name = ReadableName(parts[0], registryDisplay, manifest);
            if (name.Length == 0)
            {
                return null;
            }

            var publisher = manifest == null ? string.Empty : MatchValue(ManifestIdentity, manifest);
            if (publisher.Length == 0 && manifest != null)
            {
                publisher = MatchValue(ManifestPublisher, manifest);
            }

            return new ProgramEntry
            {
                Name = name,
                UninstallString = "remove-appx:" + fullName,
                QuietUninstallString = "remove-appx:" + fullName,
                InstallLocation = installLocation,
                Publisher = CleanPublisher(publisher),
                Version = parts[1].Trim(),
                Source = ProgramSource.Store,
                PackageFullName = fullName,
                PackageFamily = parts[0] + "_" + parts[4]
            };
        }

        private static string ReadableName(string packageName, string registryDisplay, string manifest)
        {
            if (IsReadable(registryDisplay))
            {
                return Clamp(registryDisplay);
            }

            if (manifest != null)
            {
                var manifestDisplay = MatchValue(ManifestDisplay, manifest);
                if (IsReadable(manifestDisplay))
                {
                    return Clamp(manifestDisplay);
                }
            }

            return Prettify(packageName);
        }

        private static bool IsReadable(string value)
        {
            var text = (value ?? string.Empty).Trim();
            return text.Length > 0 &&
                   !text.StartsWith("@{", StringComparison.Ordinal) &&
                   !text.StartsWith("ms-resource:", StringComparison.OrdinalIgnoreCase);
        }

        private static string ReadManifest(string installLocation)
        {
            if (string.IsNullOrWhiteSpace(installLocation))
            {
                return null;
            }

            try
            {
                var path = Path.Combine(installLocation, "AppxManifest.xml");
                return File.Exists(path) ? File.ReadAllText(path) : null;
            }
            catch (IOException)
            {
                return null;
            }
            catch (UnauthorizedAccessException)
            {
                return null;
            }
            catch (System.Security.SecurityException)
            {
                return null;
            }
        }

        private static string MatchValue(Regex pattern, string text)
        {
            var match = pattern.Match(text ?? string.Empty);
            return match.Success ? match.Groups["value"].Value.Trim() : string.Empty;
        }

        public static List<ProgramEntry> Parse(string output)
        {
            var tiles = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            var packages = new List<string[]>();

            foreach (var line in (output ?? string.Empty).Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries))
            {
                var fields = line.Split('\t');
                if (fields.Length < 3)
                {
                    continue;
                }

                if (fields[0] == "T")
                {
                    var appId = fields[1];
                    var friendly = fields[2].Trim();
                    var separator = appId.IndexOf('!');
                    if (friendly.Length == 0 || separator <= 0)
                    {
                        continue;
                    }

                    var family = appId.Substring(0, separator);
                    if (!tiles.ContainsKey(family))
                    {
                        tiles[family] = friendly;
                    }
                }
                else if (fields[0] == "P" && fields.Length >= 7)
                {
                    packages.Add(fields);
                }
            }

            var programs = new List<ProgramEntry>();
            foreach (var fields in packages)
            {
                var rawName = fields[1].Trim();
                var fullName = fields[2].Trim();
                var family = fields[3].Trim();
                if (fullName.Length == 0)
                {
                    continue;
                }

                string name;
                if (tiles.TryGetValue(family, out var friendly) && friendly.Length > 0)
                {
                    name = friendly;
                }
                else if (GuidLike.IsMatch(rawName))
                {
                    continue;
                }
                else
                {
                    name = Prettify(rawName);
                }

                if (name.Length == 0)
                {
                    continue;
                }

                programs.Add(new ProgramEntry
                {
                    Name = name,
                    UninstallString = "remove-appx:" + fullName,
                    QuietUninstallString = "remove-appx:" + fullName,
                    InstallLocation = fields[6].Trim(),
                    Publisher = CleanPublisher(fields[4]),
                    Version = fields[5].Trim(),
                    Source = ProgramSource.Store,
                    PackageFullName = fullName,
                    PackageFamily = family
                });
            }

            return programs
                .OrderBy(item => item.Name, StringComparer.OrdinalIgnoreCase)
                .ToList();
        }

        public static void SaveCache(IEnumerable<ProgramEntry> programs)
        {
            var payload = new StoreCacheDto
            {
                SavedAt = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                Programs = programs.Select(ProgramDto.FromProgram).ToArray()
            };

            var temporary = AppPaths.StoreCacheFile + ".tmp";
            try
            {
                using (var stream = File.Create(temporary))
                {
                    var serializer = new DataContractJsonSerializer(typeof(StoreCacheDto));
                    serializer.WriteObject(stream, payload);
                }

                if (File.Exists(AppPaths.StoreCacheFile))
                {
                    File.Delete(AppPaths.StoreCacheFile);
                }

                File.Move(temporary, AppPaths.StoreCacheFile);
            }
            catch (IOException exception)
            {
                Log.Warn("Could not save the Store cache: " + exception.Message);
                TryDelete(temporary);
            }
            catch (UnauthorizedAccessException exception)
            {
                Log.Warn("Could not save the Store cache: " + exception.Message);
                TryDelete(temporary);
            }
        }

        public static void InvalidateCache()
        {
            TryDelete(AppPaths.StoreCacheFile);
            TryDelete(AppPaths.StoreCacheFile + ".tmp");
        }

        public static (List<ProgramEntry> Programs, bool Fresh) LoadCache()
        {
            try
            {
                if (!File.Exists(AppPaths.StoreCacheFile))
                {
                    return (new List<ProgramEntry>(), false);
                }

                StoreCacheDto payload;
                using (var stream = File.OpenRead(AppPaths.StoreCacheFile))
                {
                    var serializer = new DataContractJsonSerializer(typeof(StoreCacheDto));
                    payload = serializer.ReadObject(stream) as StoreCacheDto;
                }

                if (payload == null || payload.Programs == null)
                {
                    return (new List<ProgramEntry>(), false);
                }

                var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
                var fresh = payload.SavedAt > 0 && now - payload.SavedAt < CacheLifetimeSeconds;
                var programs = payload.Programs
                    .Select(item => item.ToProgram())
                    .Where(item => item.Name.Length > 0 && item.PackageFullName.Length > 0)
                    .OrderBy(item => item.Name, StringComparer.OrdinalIgnoreCase)
                    .ToList();

                return (programs, fresh);
            }
            catch (IOException)
            {
                return (new List<ProgramEntry>(), false);
            }
            catch (UnauthorizedAccessException)
            {
                return (new List<ProgramEntry>(), false);
            }
            catch (System.Runtime.Serialization.SerializationException)
            {
                return (new List<ProgramEntry>(), false);
            }
        }

        public static string BuildRemovalScript(string packageFullName)
        {
            var escaped = (packageFullName ?? string.Empty).Replace("'", "''");
            return "$ErrorActionPreference='Stop'\r\n" +
                   "try { Remove-AppxPackage -Package '" + escaped + "' } " +
                   "catch { Write-Error $_; exit 1 }\r\n";
        }

        private static string CleanPublisher(string raw)
        {
            var text = (raw ?? string.Empty).Trim();
            if (text.Length == 0)
            {
                return string.Empty;
            }

            if (!text.StartsWith("CN=", StringComparison.Ordinal))
            {
                return Clamp(text);
            }

            var parts = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var chunk in text.Split(','))
            {
                var separator = chunk.IndexOf('=');
                if (separator <= 0)
                {
                    continue;
                }

                var key = chunk.Substring(0, separator).Trim().ToUpperInvariant();
                var value = chunk.Substring(separator + 1).Trim();
                if (!parts.ContainsKey(key))
                {
                    parts[key] = value;
                }
            }

            var commonName = parts.TryGetValue("CN", out var cn) ? cn : string.Empty;
            var compact = commonName.Replace(" ", string.Empty);
            var looksLikeHash = PackageHash.IsMatch(compact) ||
                                (commonName.Length > 0 &&
                                 commonName == commonName.ToUpperInvariant() &&
                                 commonName.Any(char.IsDigit) &&
                                 !commonName.Contains(" "));

            if (looksLikeHash && parts.TryGetValue("O", out var organization))
            {
                commonName = organization;
            }

            return Clamp(commonName);
        }

        private static string Prettify(string name)
        {
            var text = (name ?? string.Empty).Trim();
            if (text.Length == 0)
            {
                return string.Empty;
            }

            var underscore = text.IndexOf('_');
            var baseName = underscore > 0 ? text.Substring(0, underscore) : text;
            var dot = baseName.IndexOf('.');
            if (dot >= 0)
            {
                baseName = baseName.Substring(dot + 1);
            }

            var readable = baseName.Replace('.', ' ').Trim();
            return readable.Length > 0 ? readable : text;
        }

        private static string Clamp(string value)
        {
            var text = value ?? string.Empty;
            return text.Length > 80 ? text.Substring(0, 80) : text;
        }

        private static void TryDelete(string path)
        {
            try
            {
                if (File.Exists(path))
                {
                    File.Delete(path);
                }
            }
            catch (IOException)
            {
            }
            catch (UnauthorizedAccessException)
            {
            }
        }
    }
}
