using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UninstallerTool.Infrastructure;
using UninstallerTool.Models;

namespace UninstallerTool.Core
{
    internal static class FileSystemService
    {
        public static IEnumerable<ScannedFile> IterFiles(string directory, Func<bool> cancelled)
        {
            if (!Safety.IsSafeProgramDirectory(directory))
            {
                yield break;
            }

            var stack = new Stack<string>();
            stack.Push(Safety.AbsolutePath(directory));

            while (stack.Count > 0)
            {
                var current = stack.Pop();
                if (cancelled != null && cancelled())
                {
                    yield break;
                }

                string[] entries;
                try
                {
                    entries = Directory.GetFiles(current);
                    var directories = Directory.GetDirectories(current);
                    foreach (var child in directories)
                    {
                        if (!Safety.IsReparsePoint(child))
                        {
                            stack.Push(child);
                        }
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

                foreach (var file in entries)
                {
                    if (cancelled != null && cancelled())
                    {
                        yield break;
                    }

                    long size;
                    try
                    {
                        size = new FileInfo(file).Length;
                    }
                    catch (IOException)
                    {
                        continue;
                    }
                    catch (UnauthorizedAccessException)
                    {
                        continue;
                    }

                    yield return new ScannedFile(file, size);
                }
            }
        }

        public static FileScan ScanDirectory(string directory, int topN, Func<bool> cancelled)
        {
            var result = new FileScan();
            if (!Safety.IsSafeProgramDirectory(directory))
            {
                return result;
            }

            var absolute = Safety.AbsolutePath(directory);
            result.Directories.Add(absolute);

            foreach (var file in IterFiles(directory, cancelled))
            {
                result.TotalCount++;
                result.TotalSize += file.Size;
                result.Files.Add(file);
            }

            result.Files = result.Files
                .OrderByDescending(item => item.Size)
                .Take(topN)
                .ToList();
            result.Truncated = result.TotalCount > topN;
            result.Cancelled = cancelled != null && cancelled();
            return result;
        }

        public static FileScan MergeScans(IEnumerable<FileScan> scans, int topN)
        {
            var merged = new FileScan();
            var files = new List<ScannedFile>();

            foreach (var scan in scans)
            {
                merged.TotalCount += scan.TotalCount;
                merged.TotalSize += scan.TotalSize;
                merged.Directories.AddRange(scan.Directories);
                merged.Truncated |= scan.Truncated;
                merged.Cancelled |= scan.Cancelled;
                files.AddRange(scan.Files);
            }

            merged.Files = files
                .OrderByDescending(item => item.Size)
                .Take(topN)
                .ToList();
            merged.Truncated |= merged.TotalCount > topN;
            return merged;
        }

        public static List<string> FindProgramDirectories(string programName, string publisher)
        {
            var name = Formatting.NormalizeName(programName);
            var publisherName = Formatting.NormalizeName(publisher);
            if (name.Length == 0)
            {
                return new List<string>();
            }

            var matches = new List<string>();
            foreach (var location in Safety.ProgramRoots())
            {
                string[] children;
                try
                {
                    children = Directory.GetDirectories(location);
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
                    if (Safety.IsReparsePoint(child))
                    {
                        continue;
                    }

                    var entryName = Formatting.NormalizeName(Path.GetFileName(child));
                    if (entryName == name)
                    {
                        matches.Add(child);
                        continue;
                    }

                    if (publisherName.Length == 0 || entryName != publisherName)
                    {
                        continue;
                    }

                    string[] grandchildren;
                    try
                    {
                        grandchildren = Directory.GetDirectories(child);
                    }
                    catch (IOException)
                    {
                        continue;
                    }
                    catch (UnauthorizedAccessException)
                    {
                        continue;
                    }

                    matches.AddRange(grandchildren
                        .Where(item => !Safety.IsReparsePoint(item))
                        .Where(item => Formatting.NormalizeName(Path.GetFileName(item)) == name));
                }
            }

            var result = new List<string>();
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var match in matches)
            {
                var normalized = Safety.NormalizePath(match);
                if (normalized.Length == 0 || !seen.Add(normalized) || !Safety.IsSafeProgramDirectory(normalized))
                {
                    continue;
                }

                result.Add(Safety.AbsolutePath(match));
            }

            return result;
        }

        public static FileScan ScanProgramFiles(ProgramEntry program, int topN, Func<bool> cancelled)
        {
            if (Safety.IsSafeProgramDirectory(program.InstallLocation))
            {
                return ScanDirectory(program.InstallLocation, topN, cancelled);
            }

            var directories = FindProgramDirectories(program.Name, program.Publisher);
            var scans = new List<FileScan>();
            foreach (var directory in directories)
            {
                if (cancelled != null && cancelled())
                {
                    break;
                }

                scans.Add(ScanDirectory(directory, topN, cancelled));
            }

            return MergeScans(scans, topN);
        }

        public static long MeasureDirectorySize(string directory, Func<bool> cancelled)
        {
            if (!Safety.IsSafeProgramDirectory(directory))
            {
                return 0;
            }

            long total = 0;
            foreach (var file in IterFiles(directory, cancelled))
            {
                total += file.Size;
            }

            return total;
        }

        public static long DirectoryStamp(string directory)
        {
            try
            {
                return Directory.GetLastWriteTimeUtc(directory).Ticks;
            }
            catch (IOException)
            {
                return 0;
            }
            catch (UnauthorizedAccessException)
            {
                return 0;
            }
        }

        public static bool RemoveFile(string path)
        {
            if (!File.Exists(path) && !Directory.Exists(path))
            {
                return false;
            }

            if (Safety.IsReparsePoint(path))
            {
                DeleteLink(path);
                return false;
            }

            try
            {
                File.Delete(path);
                return false;
            }
            catch (FileNotFoundException)
            {
                return false;
            }
            catch (DirectoryNotFoundException)
            {
                return false;
            }
            catch (IOException)
            {
                return RetryRemove(path);
            }
            catch (UnauthorizedAccessException)
            {
                return RetryRemove(path);
            }
        }

        public static (bool Removed, int Scheduled, List<string> Errors) RemoveTree(string path)
        {
            var errors = new List<string>();
            var scheduled = 0;
            var removed = RemoveTreeInner(path, errors, ref scheduled, new HashSet<string>(StringComparer.Ordinal));
            return (removed, scheduled, errors);
        }

        private static bool RemoveTreeInner(string path, List<string> errors, ref int scheduled, HashSet<string> visited)
        {
            var normalized = Safety.NormalizePath(path);
            if (normalized.Length == 0 || !visited.Add(normalized))
            {
                return true;
            }

            if (!File.Exists(normalized) && !Directory.Exists(normalized))
            {
                return true;
            }

            if (Safety.IsReparsePoint(normalized))
            {
                try
                {
                    DeleteLink(normalized);
                    return true;
                }
                catch (IOException exception)
                {
                    errors.Add(path + ": " + exception.Message);
                    return false;
                }
                catch (UnauthorizedAccessException exception)
                {
                    errors.Add(path + ": " + exception.Message);
                    return false;
                }
            }

            if (File.Exists(normalized))
            {
                try
                {
                    if (RemoveFile(normalized))
                    {
                        scheduled++;
                        return false;
                    }

                    return true;
                }
                catch (IOException exception)
                {
                    errors.Add(path + ": " + exception.Message);
                    return false;
                }
                catch (UnauthorizedAccessException exception)
                {
                    errors.Add(path + ": " + exception.Message);
                    return false;
                }
            }

            var removed = true;
            string[] children;
            try
            {
                children = Directory.GetFileSystemEntries(normalized);
            }
            catch (DirectoryNotFoundException)
            {
                return true;
            }
            catch (IOException exception)
            {
                errors.Add(path + ": " + exception.Message);
                return false;
            }
            catch (UnauthorizedAccessException exception)
            {
                errors.Add(path + ": " + exception.Message);
                return false;
            }

            foreach (var child in children)
            {
                if (!RemoveTreeInner(child, errors, ref scheduled, visited))
                {
                    removed = false;
                }
            }

            try
            {
                Directory.Delete(normalized, false);
                return removed;
            }
            catch (DirectoryNotFoundException)
            {
                return removed;
            }
            catch (IOException)
            {
                if (NativeMethods.ScheduleDelete(normalized))
                {
                    scheduled++;
                }

                return false;
            }
            catch (UnauthorizedAccessException)
            {
                if (NativeMethods.ScheduleDelete(normalized))
                {
                    scheduled++;
                }

                return false;
            }
        }

        private static bool RetryRemove(string path)
        {
            try
            {
                File.SetAttributes(path, FileAttributes.Normal);
                File.Delete(path);
                return false;
            }
            catch (FileNotFoundException)
            {
                return false;
            }
            catch (IOException)
            {
                return NativeMethods.ScheduleDelete(path);
            }
            catch (UnauthorizedAccessException)
            {
                return NativeMethods.ScheduleDelete(path);
            }
        }

        private static void DeleteLink(string path)
        {
            if (Directory.Exists(path) && !File.Exists(path))
            {
                Directory.Delete(path, false);
                return;
            }

            File.Delete(path);
        }
    }
}
