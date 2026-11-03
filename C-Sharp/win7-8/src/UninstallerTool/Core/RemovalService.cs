using System;
using System.Collections.Generic;
using System.IO;
using UninstallerTool.Infrastructure;
using UninstallerTool.Models;

namespace UninstallerTool.Core
{
    internal static class RemovalService
    {
        public static RemovalResult RemoveLeftovers(Leftovers leftovers, string backupDirectory = null)
        {
            var result = new RemovalResult();
            var roots = Safety.RemovalRoots();

            foreach (var path in leftovers.Files)
            {
                RemovePath(path, roots, result);
            }

            if (leftovers.Registry.Count > 0)
            {
                var directory = string.IsNullOrWhiteSpace(backupDirectory)
                    ? AppPaths.BackupDirectory
                    : backupDirectory;

                foreach (var entry in leftovers.Registry)
                {
                    RemoveRegistryEntry(entry, result, directory);
                }
            }

            Log.Info(string.Format(
                "Removal finished: {0} files, {1} registry keys, {2} scheduled",
                result.RemovedFiles,
                result.RemovedRegistry,
                result.ScheduledFiles));

            return result;
        }

        private static void RemovePath(string path, string[] roots, RemovalResult result)
        {
            var normalized = Safety.NormalizePath(path);
            if (normalized.Length == 0)
            {
                return;
            }

            if (!Directory.Exists(normalized) && !File.Exists(normalized))
            {
                return;
            }

            if (!Safety.IsSafeRemovalPath(normalized, roots))
            {
                result.Errors.Add("Skipped unsafe path: " + path);
                Log.Warn("Skipped unsafe leftover path: " + path);
                return;
            }

            if (Safety.IsReparsePoint(normalized))
            {
                try
                {
                    if (FileSystemService.RemoveFile(normalized))
                    {
                        result.ScheduledFiles++;
                    }
                    else
                    {
                        result.RemovedFiles++;
                    }
                }
                catch (IOException exception)
                {
                    result.Errors.Add("Could not remove " + path + ": " + exception.Message);
                }
                catch (UnauthorizedAccessException exception)
                {
                    result.Errors.Add("Could not remove " + path + ": " + exception.Message);
                }

                return;
            }

            if (Directory.Exists(normalized))
            {
                var (removed, scheduled, errors) = FileSystemService.RemoveTree(normalized);
                if (removed)
                {
                    result.RemovedFiles++;
                }

                result.ScheduledFiles += scheduled;
                result.Errors.AddRange(errors);
                return;
            }

            try
            {
                if (FileSystemService.RemoveFile(normalized))
                {
                    result.ScheduledFiles++;
                }
                else
                {
                    result.RemovedFiles++;
                }
            }
            catch (IOException exception)
            {
                result.Errors.Add("Could not remove " + path + ": " + exception.Message);
            }
            catch (UnauthorizedAccessException exception)
            {
                result.Errors.Add("Could not remove " + path + ": " + exception.Message);
            }
        }

        private static void RemoveRegistryEntry(RegistryEntry entry, RemovalResult result, string directory)
        {
            if (!RegistrySnapshot.IsSafeEntry(entry))
            {
                result.Errors.Add("Skipped unsafe registry key: " + entry.Path);
                Log.Warn("Skipped unsafe registry key: " + entry.Path);
                return;
            }

            string backup;
            try
            {
                backup = RegistrySnapshot.ExportKey(entry, directory);
            }
            catch (IOException exception)
            {
                result.Errors.Add("Could not back up " + entry.Path + ": " + exception.Message);
                return;
            }
            catch (UnauthorizedAccessException exception)
            {
                result.Errors.Add("Could not back up " + entry.Path + ": " + exception.Message);
                return;
            }

            result.Backups.Add(backup);

            try
            {
                RegistrySnapshot.DeleteEntry(entry);
            }
            catch (IOException exception)
            {
                result.Errors.Add("Could not remove " + entry.Path + ": " + exception.Message);
                return;
            }
            catch (UnauthorizedAccessException exception)
            {
                result.Errors.Add("Could not remove " + entry.Path + ": " + exception.Message);
                return;
            }
            catch (System.Security.SecurityException exception)
            {
                result.Errors.Add("Could not remove " + entry.Path + ": " + exception.Message);
                return;
            }

            result.RemovedRegistry++;
        }

        public static List<string> FilterRemovable(IEnumerable<string> files)
        {
            var roots = Safety.RemovalRoots();
            var result = new List<string>();
            foreach (var file in files)
            {
                if (Safety.IsSafeRemovalPath(file, roots))
                {
                    result.Add(file);
                }
            }

            return result;
        }
    }
}
