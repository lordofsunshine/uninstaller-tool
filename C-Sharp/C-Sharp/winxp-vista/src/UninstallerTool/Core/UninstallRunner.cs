using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using UninstallerTool.Infrastructure;
using UninstallerTool.Models;

namespace UninstallerTool.Core
{
    internal sealed class UninstallRunner
    {
        private const double SilentTimeoutSeconds = 300;
        private const double SettleSeconds = 4;
        private const double StatsSeconds = 1.5;
        private const int PollMilliseconds = 250;

        private sealed class ExecutionOutcome
        {
            public int? ExitCode;

            public bool StillRunning;

            public string Message = string.Empty;
        }

        public async Task<UninstallSummary> RunAsync(
            IList<ProgramEntry> programs,
            bool silent,
            IProgress<UninstallProgress> progress,
            IProgress<string> stats,
            CancellationToken token)
        {
            var summary = new UninstallSummary();
            var total = programs.Count;

            for (var index = 0; index < programs.Count; index++)
            {
                if (token.IsCancellationRequested)
                {
                    break;
                }

                var program = programs[index];
                progress?.Report(new UninstallProgress
                {
                    Done = index,
                    Total = total,
                    ProgramKey = program.Key,
                    Status = ProgramStatus.Running,
                    Message = "Uninstalling " + program.Name + "\u2026"
                });

                UninstallResult outcome;
                try
                {
                    outcome = program.IsStoreApp
                        ? await RunStoreAsync(program, token).ConfigureAwait(false)
                        : await RunClassicAsync(program, silent, progress, stats, token).ConfigureAwait(false);
                }
                catch (TimeoutException)
                {
                    outcome = Failure("Uninstall timed out for " + program.Name);
                }
                catch (FileNotFoundException exception)
                {
                    outcome = Failure(exception.Message);
                }
                catch (IOException exception)
                {
                    Log.Warn("Could not uninstall " + program.Name + ": " + exception.Message);
                    outcome = Failure(exception.Message);
                }
                catch (InvalidOperationException exception)
                {
                    Log.Warn("Could not uninstall " + program.Name + ": " + exception.Message);
                    outcome = Failure(exception.Message);
                }
                catch (Exception exception)
                {
                    Log.Exception("Unexpected uninstall error for " + program.Name, exception);
                    outcome = Failure(exception.Message.Length > 0 ? exception.Message : exception.GetType().Name);
                }

                if (token.IsCancellationRequested)
                {
                    outcome.Success = false;
                    outcome.Message = "Uninstall cancelled for " + program.Name;
                }

                outcome.ProgramKey = program.Key;
                outcome.Name = program.Name;
                summary.Results.Add(outcome);

                if (outcome.Success)
                {
                    if (outcome.RebootRequired)
                    {
                        summary.RebootRequired.Add(program.Name);
                    }

                    if (!outcome.StillRunning)
                    {
                        summary.Uninstalled.Add(program);
                        if (outcome.Message.Length == 0)
                        {
                            outcome.Message = program.Name + " was uninstalled";
                        }
                    }
                    else if (outcome.Message.Length == 0)
                    {
                        outcome.Message = "The uninstaller is still finishing in the background";
                    }
                }
                else if (outcome.Message.Length == 0)
                {
                    outcome.Message = outcome.ExitCode.HasValue
                        ? "Uninstaller for " + program.Name + " exited with code " + outcome.ExitCode.Value
                        : "Could not uninstall " + program.Name;
                }

                Log.Info(string.Format(
                    "{0}: success={1} code={2} message={3}",
                    program.Name,
                    outcome.Success,
                    outcome.ExitCode,
                    outcome.Message));

                progress?.Report(new UninstallProgress
                {
                    Done = index + 1,
                    Total = total,
                    ProgramKey = program.Key,
                    Status = outcome.Success ? ProgramStatus.Success : ProgramStatus.Error,
                    Message = outcome.Message
                });

                stats?.Report(string.Empty);
            }

            return summary;
        }

        private async Task<UninstallResult> RunClassicAsync(
            ProgramEntry program,
            bool silent,
            IProgress<UninstallProgress> progress,
            IProgress<string> stats,
            CancellationToken token)
        {
            var quiet = silent ? program.QuietUninstallString : string.Empty;
            var arguments = UninstallCommands.BuildUninstallCommand(
                quiet.Length > 0 ? quiet : program.UninstallString,
                silent);

            if (arguments.Count == 0 || !UninstallCommands.CommandExists(arguments))
            {
                throw new FileNotFoundException("The uninstall command was not found for " + program.Name);
            }

            var timeout = silent ? TimeSpan.FromSeconds(SilentTimeoutSeconds) : (TimeSpan?)null;
            var outcome = await ExecuteAsync(arguments, timeout, stats, token).ConfigureAwait(false);
            if (!outcome.ExitCode.HasValue)
            {
                return new UninstallResult { StillRunning = outcome.StillRunning, Message = outcome.Message };
            }

            var code = outcome.ExitCode.Value;
            var success = UninstallCommands.ExitCodeSucceeded(arguments, code) || UninstallCommands.IsRebootCode(code);

            if (!success && silent && !token.IsCancellationRequested)
            {
                progress?.Report(new UninstallProgress
                {
                    Done = 0,
                    Total = 0,
                    ProgramKey = program.Key,
                    Status = ProgramStatus.Running,
                    Message = "Silent mode failed for " + program.Name + "; opening the uninstaller\u2026"
                });

                var fallback = UninstallCommands.BuildUninstallCommand(program.UninstallString, false);
                if (fallback.Count > 0 && UninstallCommands.CommandExists(fallback))
                {
                    var second = await ExecuteAsync(fallback, null, stats, token).ConfigureAwait(false);
                    code = second.ExitCode ?? 0;
                    success = second.ExitCode.HasValue &&
                              (UninstallCommands.ExitCodeSucceeded(fallback, code) || UninstallCommands.IsRebootCode(code));
                    outcome.StillRunning = second.StillRunning;
                    outcome.Message = second.Message;
                }
            }

            return new UninstallResult
            {
                Success = success,
                ExitCode = code,
                RebootRequired = UninstallCommands.IsRebootCode(code),
                StillRunning = outcome.StillRunning,
                Message = outcome.Message
            };
        }

        private async Task<UninstallResult> RunStoreAsync(ProgramEntry program, CancellationToken token)
        {
            if (program.PackageFullName.Length == 0)
            {
                return Failure("The Store package identifier is missing");
            }

            var script = StoreApps.BuildRemovalScript(program.PackageFullName);
            var result = await PowerShellRunner
                .RunAsync(script, TimeSpan.FromSeconds(SilentTimeoutSeconds))
                .ConfigureAwait(false);

            return new UninstallResult
            {
                Success = result.ExitCode == 0,
                ExitCode = result.ExitCode,
                Message = result.ExitCode == 0 ? string.Empty : result.Error.Trim()
            };
        }

        private async Task<ExecutionOutcome> ExecuteAsync(
            List<string> arguments,
            TimeSpan? timeout,
            IProgress<string> stats,
            CancellationToken token)
        {
            var prepared = UninstallCommands.PrepareProcessArguments(arguments);
            var startInfo = new ProcessStartInfo
            {
                FileName = prepared[0],
                Arguments = UninstallCommands.QuoteCommandLine(prepared.Skip(1)),
                UseShellExecute = false,
                CreateNoWindow = true,
                WindowStyle = ProcessWindowStyle.Hidden
            };

            Log.Info("Starting uninstaller: " + UninstallCommands.QuoteCommandLine(prepared));

            var process = Process.Start(startInfo);
            if (process == null)
            {
                throw new InvalidOperationException("Could not start the uninstaller");
            }

            var approved = new HashSet<int>();
            var clock = Stopwatch.StartNew();
            var lastStats = 0d;

            using (process)
            {
                while (true)
                {
                    if (token.IsCancellationRequested)
                    {
                        ProcessService.KillTree(process.Id);
                        return new ExecutionOutcome { Message = "Cancelled" };
                    }

                    if (process.WaitForExit(PollMilliseconds))
                    {
                        break;
                    }

                    foreach (var pid in ProcessService.DescendantPids(process.Id))
                    {
                        approved.Add(pid);
                    }

                    var elapsed = clock.Elapsed.TotalSeconds;
                    if (timeout.HasValue && elapsed >= timeout.Value.TotalSeconds)
                    {
                        ProcessService.KillTree(process.Id);
                        throw new TimeoutException();
                    }

                    if (elapsed - lastStats >= StatsSeconds)
                    {
                        lastStats = elapsed;
                        stats?.Report(string.Format(
                            "Elapsed: {0:0} s   |   Memory usage: {1:0.0} MB",
                            elapsed,
                            ProcessService.TreeMemoryMb(process.Id)));
                    }
                }

                var exitCode = process.ExitCode;
                var stillRunning = await SettleAsync(approved, token).ConfigureAwait(false);
                if (stillRunning)
                {
                    Log.Warn("Uninstaller process " + process.Id + " finished, but child processes are still running");
                }

                return new ExecutionOutcome { ExitCode = exitCode, StillRunning = stillRunning };
            }
        }

        private static async Task<bool> SettleAsync(HashSet<int> approved, CancellationToken token)
        {
            if (approved.Count == 0)
            {
                return false;
            }

            var deadline = DateTime.UtcNow.AddSeconds(SettleSeconds);
            while (DateTime.UtcNow < deadline)
            {
                if (token.IsCancellationRequested)
                {
                    return false;
                }

                var alive = new HashSet<int>();
                foreach (var pid in approved)
                {
                    using (var process = TryGetProcess(pid))
                    {
                        if (process != null)
                        {
                            alive.Add(pid);
                        }
                    }
                }

                foreach (var pid in alive.ToArray())
                {
                    foreach (var child in ProcessService.DescendantPids(pid))
                    {
                        if (approved.Add(child))
                        {
                            alive.Add(child);
                        }
                    }
                }

                if (alive.Count == 0)
                {
                    return false;
                }

                await TaskEx.Delay(200, token).ConfigureAwait(false);
            }

            return approved.Count > 0;
        }

        private static Process TryGetProcess(int pid)
        {
            try
            {
                var process = Process.GetProcessById(pid);
                if (!process.HasExited)
                {
                    return process;
                }

                process.Dispose();
                return null;
            }
            catch (ArgumentException)
            {
                return null;
            }
            catch (InvalidOperationException)
            {
                return null;
            }
        }

        private static UninstallResult Failure(string message)
        {
            return new UninstallResult { Success = false, Message = message ?? string.Empty };
        }
    }
}
