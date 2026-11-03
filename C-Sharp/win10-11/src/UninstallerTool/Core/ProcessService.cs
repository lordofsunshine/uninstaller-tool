using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading;
using UninstallerTool.Infrastructure;
using UninstallerTool.Models;

namespace UninstallerTool.Core
{
    internal static class ProcessService
    {
        private sealed class ProcessNode
        {
            public int Pid;
            public int ParentPid;
            public string Name;
        }

        public static List<ProcessEntry> ScanProcesses()
        {
            var entries = new List<ProcessEntry>();
            foreach (var process in Process.GetProcesses())
            {
                using (process)
                {
                    try
                    {
                        var executable = process.MainModule?.FileName ?? string.Empty;
                        var name = executable.Length > 0
                            ? Path.GetFileName(executable)
                            : process.ProcessName;
                        entries.Add(new ProcessEntry(process.Id, name, Safety.NormalizePath(executable)));
                    }
                    catch (System.ComponentModel.Win32Exception)
                    {
                    }
                    catch (InvalidOperationException)
                    {
                    }
                    catch (NotSupportedException)
                    {
                    }
                }
            }

            return entries;
        }

        public static HashSet<string> ProgramPaths(ProgramEntry program)
        {
            var paths = new HashSet<string>(StringComparer.Ordinal);

            if (Safety.IsSafeProgramDirectory(program.InstallLocation))
            {
                paths.Add(Safety.NormalizePath(program.InstallLocation));
            }

            var icon = Formatting.SplitIconReference(program.Icon);
            if (Formatting.IsFile(icon.Path))
            {
                var directory = Path.GetDirectoryName(icon.Path) ?? string.Empty;
                if (Safety.IsSafeProgramDirectory(directory))
                {
                    paths.Add(Safety.NormalizePath(directory));
                }
            }

            foreach (var command in new[] { program.UninstallString, program.QuietUninstallString })
            {
                var parts = UninstallCommands.SplitWindowsCommand(command);
                if (parts.Count == 0 || !Formatting.IsFile(parts[0]))
                {
                    continue;
                }

                var directory = Path.GetDirectoryName(parts[0]) ?? string.Empty;
                if (Safety.IsSafeProgramDirectory(directory))
                {
                    paths.Add(Safety.NormalizePath(directory));
                }
            }

            paths.Remove(string.Empty);
            return paths;
        }

        public static List<ProcessEntry> FindRunning(ProgramEntry program, IReadOnlyList<ProcessEntry> snapshot = null)
        {
            var roots = ProgramPaths(program).OrderBy(item => item, StringComparer.Ordinal).ToList();
            if (roots.Count == 0)
            {
                return new List<ProcessEntry>();
            }

            var entries = snapshot ?? ScanProcesses();
            var matches = new List<ProcessEntry>();
            foreach (var entry in entries)
            {
                if (entry.Executable.Length == 0)
                {
                    continue;
                }

                foreach (var root in roots)
                {
                    if (entry.Executable == root ||
                        entry.Executable.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.Ordinal))
                    {
                        matches.Add(entry);
                        break;
                    }
                }
            }

            return matches;
        }

        public static Dictionary<string, List<ProcessEntry>> BatchFindRunning(IEnumerable<ProgramEntry> programs)
        {
            var snapshot = ScanProcesses();
            var result = new Dictionary<string, List<ProcessEntry>>(StringComparer.Ordinal);
            foreach (var program in programs)
            {
                result[program.Key] = FindRunning(program, snapshot);
            }

            return result;
        }

        public static (int Killed, List<string> Errors) KillProcesses(
            IEnumerable<ProcessEntry> entries,
            double timeoutSeconds = 5)
        {
            var killed = 0;
            var errors = new List<string>();
            var targets = new List<Process>();

            foreach (var entry in entries)
            {
                try
                {
                    targets.Add(Process.GetProcessById(entry.Pid));
                }
                catch (ArgumentException)
                {
                }
                catch (InvalidOperationException)
                {
                }
            }

            foreach (var target in targets)
            {
                try
                {
                    foreach (var childPid in DescendantPids(target.Id).Where(pid => pid != target.Id))
                    {
                        try
                        {
                            using (var child = Process.GetProcessById(childPid))
                            {
                                child.Kill();
                                killed++;
                            }
                        }
                        catch (ArgumentException)
                        {
                        }
                        catch (InvalidOperationException)
                        {
                        }
                        catch (System.ComponentModel.Win32Exception exception)
                        {
                            errors.Add(exception.Message);
                        }
                    }

                    target.Kill();
                    killed++;
                }
                catch (InvalidOperationException)
                {
                }
                catch (System.ComponentModel.Win32Exception exception)
                {
                    errors.Add(exception.Message);
                }
            }

            var deadline = DateTime.UtcNow.AddSeconds(timeoutSeconds);
            while (DateTime.UtcNow < deadline)
            {
                if (targets.All(item => !IsRunning(item.Id)))
                {
                    break;
                }

                Thread.Sleep(50);
            }

            foreach (var target in targets)
            {
                target.Dispose();
            }

            return (killed, errors);
        }

        public static List<int> DescendantPids(int pid)
        {
            var nodes = QueryNodes();
            var result = new List<int> { pid };
            if (nodes.Count == 0)
            {
                return result;
            }

            var queue = new Queue<int>();
            queue.Enqueue(pid);
            var seen = new HashSet<int> { pid };

            while (queue.Count > 0)
            {
                var current = queue.Dequeue();
                foreach (var node in nodes.Values.Where(item => item.ParentPid == current))
                {
                    if (!seen.Add(node.Pid))
                    {
                        continue;
                    }

                    result.Add(node.Pid);
                    queue.Enqueue(node.Pid);
                }
            }

            return result;
        }

        public static double TreeMemoryMb(int pid)
        {
            long total = 0;
            foreach (var current in DescendantPids(pid))
            {
                try
                {
                    using (var process = Process.GetProcessById(current))
                    {
                        total += process.WorkingSet64;
                    }
                }
                catch (ArgumentException)
                {
                }
                catch (InvalidOperationException)
                {
                }
                catch (System.ComponentModel.Win32Exception)
                {
                }
            }

            return total / (1024d * 1024d);
        }

        public static bool WaitForTree(int pid, double timeoutSeconds)
        {
            var deadline = DateTime.UtcNow.AddSeconds(timeoutSeconds);
            while (DateTime.UtcNow < deadline)
            {
                var alive = DescendantPids(pid).Count(pid2 => IsRunning(pid2));
                if (alive == 0)
                {
                    return true;
                }

                Thread.Sleep(100);
            }

            return false;
        }

        public static void KillTree(int pid)
        {
            var pids = DescendantPids(pid);
            for (var index = pids.Count - 1; index >= 0; index--)
            {
                try
                {
                    using (var process = Process.GetProcessById(pids[index]))
                    {
                        process.Kill();
                    }
                }
                catch (ArgumentException)
                {
                }
                catch (InvalidOperationException)
                {
                }
                catch (System.ComponentModel.Win32Exception)
                {
                }
            }
        }

        private static bool IsRunning(int pid)
        {
            try
            {
                using (var process = Process.GetProcessById(pid))
                {
                    return !process.HasExited;
                }
            }
            catch (ArgumentException)
            {
                return false;
            }
            catch (InvalidOperationException)
            {
                return false;
            }
        }

        private static Dictionary<int, ProcessNode> QueryNodes()
        {
            var nodes = new Dictionary<int, ProcessNode>();
            try
            {
                foreach (var entry in NativeMethods.EnumerateProcesses())
                {
                    var pid = (int)entry.ProcessId;
                    nodes[pid] = new ProcessNode
                    {
                        Pid = pid,
                        ParentPid = (int)entry.ParentProcessId,
                        Name = entry.Executable ?? string.Empty
                    };
                }
            }
            catch (InvalidOperationException)
            {
            }
            catch (UnauthorizedAccessException)
            {
            }

            return nodes;
        }
    }
}
