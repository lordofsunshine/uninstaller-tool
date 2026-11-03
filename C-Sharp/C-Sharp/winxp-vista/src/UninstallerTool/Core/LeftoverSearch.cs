using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using UninstallerTool.Infrastructure;
using UninstallerTool.Models;

namespace UninstallerTool.Core
{
    internal static class LeftoverSearch
    {
        public static Leftovers Search(
            ProgramEntry program,
            RegistrySnapshot snapshot,
            double budgetSeconds,
            Func<bool> cancelled)
        {
            var result = new Leftovers
            {
                ProgramKey = program.Key,
                ProgramName = program.Name
            };

            var targetName = Formatting.NormalizeName(program.Name);
            var targetPublisher = Formatting.NormalizeName(program.Publisher);
            if (targetName.Length == 0)
            {
                return result;
            }

            var clock = Stopwatch.StartNew();
            var files = new List<string>();

            bool ShouldStop()
            {
                return (cancelled != null && cancelled()) || clock.Elapsed.TotalSeconds >= budgetSeconds;
            }

            if (program.PackageFamily.Length > 0)
            {
                var packages = Path.Combine(
                    Environment.GetEnvironmentVariable("LOCALAPPDATA") ?? string.Empty,
                    "Packages");
                var candidate = Path.Combine(packages, program.PackageFamily);
                if (Directory.Exists(candidate) && Safety.IsSafeRemovalPath(candidate, Safety.RemovalRoots()))
                {
                    files.Add(Safety.AbsolutePath(candidate));
                }
            }

            foreach (var location in Safety.ProgramRoots().Concat(Safety.ExtraRoots()))
            {
                if (ShouldStop())
                {
                    result.TimedOut = true;
                    break;
                }

                if (CollectFromRoot(location, targetName, targetPublisher, files, ShouldStop))
                {
                    result.TimedOut = true;
                    break;
                }
            }

            var unique = new List<string>();
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var path in files)
            {
                var normalized = Safety.NormalizePath(path);
                if (normalized.Length == 0 || !seen.Add(normalized))
                {
                    continue;
                }

                if (!Directory.Exists(normalized) && !File.Exists(normalized))
                {
                    continue;
                }

                if (!Safety.IsSafeRemovalPath(normalized, Safety.RemovalRoots()))
                {
                    continue;
                }

                unique.Add(Safety.AbsolutePath(path));
            }

            unique.Sort(StringComparer.OrdinalIgnoreCase);
            result.Files = unique;

            if (snapshot != null && !result.TimedOut)
            {
                result.Registry = snapshot
                    .Find(program.Name, program.Publisher)
                    .Where(RegistrySnapshot.IsSafeEntry)
                    .OrderBy(entry => entry.Path, StringComparer.OrdinalIgnoreCase)
                    .ToList();
            }

            Log.Info(string.Format(
                "Leftovers for {0}: {1} paths, {2} registry keys",
                program.Name,
                result.Files.Count,
                result.Registry.Count));

            return result;
        }

        private static bool CollectFromRoot(
            string location,
            string targetName,
            string targetPublisher,
            List<string> found,
            Func<bool> shouldStop)
        {
            string[] directories;
            try
            {
                directories = Directory.GetDirectories(location);
            }
            catch (IOException)
            {
                return false;
            }
            catch (UnauthorizedAccessException)
            {
                return false;
            }

            foreach (var directory in directories)
            {
                if (shouldStop())
                {
                    return true;
                }

                if (Safety.IsReparsePoint(directory))
                {
                    continue;
                }

                var entryName = Formatting.NormalizeName(Path.GetFileName(directory));
                if (entryName == targetName)
                {
                    found.Add(directory);
                    continue;
                }

                if (targetPublisher.Length > 0 && entryName == targetPublisher)
                {
                    string[] children;
                    try
                    {
                        children = Directory.GetDirectories(directory);
                    }
                    catch (IOException)
                    {
                        continue;
                    }
                    catch (UnauthorizedAccessException)
                    {
                        continue;
                    }

                    foreach (var child in children)
                    {
                        if (shouldStop())
                        {
                            return true;
                        }

                        if (!Safety.IsReparsePoint(child) &&
                            Formatting.NormalizeName(Path.GetFileName(child)) == targetName)
                        {
                            found.Add(child);
                        }
                    }

                    continue;
                }

                if (VersionedMatch(entryName, targetName))
                {
                    found.Add(directory);
                }
            }

            return false;
        }

        private static bool VersionedMatch(string entryName, string target)
        {
            if (target.Length < 4 || !entryName.StartsWith(target, StringComparison.Ordinal))
            {
                return false;
            }

            var remainder = entryName.Substring(target.Length);
            if (remainder.Length == 0 || remainder.Length > 24)
            {
                return false;
            }

            return remainder.Any(char.IsDigit);
        }
    }
}
