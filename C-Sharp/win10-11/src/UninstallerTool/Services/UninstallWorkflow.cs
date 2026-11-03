using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using UninstallerTool.Core;
using UninstallerTool.Infrastructure;
using UninstallerTool.Models;
using UninstallerTool.ViewModels;
using UninstallerTool.Views.Dialogs;

namespace UninstallerTool.Services
{
    internal sealed class UninstallWorkflow
    {
        private const double LeftoverBudgetSeconds = 40;

        private readonly Window _owner;
        private readonly MainViewModel _viewModel;

        public UninstallWorkflow(Window owner, MainViewModel viewModel)
        {
            _owner = owner;
            _viewModel = viewModel;
        }

        public async Task<bool> RunAsync(IReadOnlyList<ProgramEntry> programs, bool silent)
        {
            if (!EnsureAdministrator())
            {
                return false;
            }

            var ready = ConfirmRunning(programs);
            if (ready == null)
            {
                return false;
            }

            if (ready.Count == 0)
            {
                _viewModel.SetStatusMessage("Nothing left to uninstall");
                return false;
            }

            _viewModel.SetBusy(true);
            _viewModel.SetProgress(true, false, 0, ready.Count);
            _viewModel.SetStatusMessage("Starting the uninstaller\u2026");

            UninstallSummary summary;
            try
            {
                var progress = new Progress<UninstallProgress>(OnProgress);
                var stats = new Progress<string>(_viewModel.AppendStatusMessage);
                var runner = new UninstallRunner();
                summary = await runner.RunAsync(ready, silent, progress, stats, CancellationToken.None);
            }
            catch (Exception exception)
            {
                Log.Exception("Uninstall failed", exception);
                _viewModel.SetBusy(false);
                _viewModel.SetProgress(false, false, 0, 1);
                MessageDialog.Show(_owner, "Uninstall error", exception.Message, MessageResult.Ok);
                return false;
            }

            if (summary.Uninstalled.Count > 0)
            {
                StoreApps.InvalidateCache();
            }

            await ReviewLeftoversAsync(summary);

            _viewModel.SetBusy(false);
            _viewModel.SetProgress(false, false, 0, 1);
            _viewModel.SetStatusMessage("Uninstallation completed");

            if (summary.RebootRequired.Count > 0)
            {
                var names = string.Join(Environment.NewLine, summary.RebootRequired.Take(10));
                MessageDialog.Show(
                    _owner,
                    "Restart required",
                    "These programs requested a restart to finish removal:" + Environment.NewLine + Environment.NewLine +
                    names + Environment.NewLine + Environment.NewLine +
                    "Please restart Windows when convenient.",
                    MessageResult.Ok);
            }

            return summary.Uninstalled.Count > 0;
        }

        private void OnProgress(UninstallProgress progress)
        {
            _viewModel.SetProgress(true, false, progress.Done, Math.Max(1, progress.Total));
            if (progress.ProgramKey.Length > 0)
            {
                _viewModel.SetStatus(progress.ProgramKey, progress.Status);
            }

            if (progress.Message.Length > 0)
            {
                _viewModel.SetStatusMessage(progress.Message);
            }
        }

        private async Task ReviewLeftoversAsync(UninstallSummary summary)
        {
            if (summary.Uninstalled.Count == 0)
            {
                _viewModel.SetStatusMessage("No programs were uninstalled");
                return;
            }

            _viewModel.SetProgress(true, true, 0, 1);
            _viewModel.SetStatusMessage("Checking for leftover files and registry entries\u2026");

            RegistrySnapshot snapshot = null;
            var budget = LeftoverBudgetSeconds;

            foreach (var program in summary.Uninstalled)
            {
                if (budget <= 0.5)
                {
                    break;
                }

                var clock = Stopwatch.StartNew();
                try
                {
                    if (snapshot == null)
                    {
                        snapshot = await Task.Run(() => RegistrySnapshot.Build());
                    }

                    var remaining = budget;
                    var model = program;
                    var currentSnapshot = snapshot;
                    var result = await Task.Run(() => LeftoverSearch.Search(model, currentSnapshot, remaining, null));
                    budget -= clock.Elapsed.TotalSeconds;

                    if (result.HasItems)
                    {
                        _viewModel.SetStatusMessage("Leftover items found");
                        var dialog = new LeftoversDialog(result) { Owner = _owner };
                        dialog.ShowDialog();
                    }
                    else
                    {
                        _viewModel.SetStatusMessage("No leftovers found for " + result.ProgramName);
                    }
                }
                catch (Exception exception)
                {
                    Log.Exception("Leftover search failed", exception);
                    _viewModel.SetStatusMessage("Leftover search failed");
                    budget -= clock.Elapsed.TotalSeconds;
                }
            }

            if (budget <= 0.5)
            {
                _viewModel.SetStatusMessage("Leftover search timed out");
            }
        }

        private bool EnsureAdministrator()
        {
            if (Elevation.IsAdmin())
            {
                return true;
            }

            Log.Warn("The application is not running with administrator rights");
            MessageDialog.Show(
                _owner,
                "Administrator rights required",
                "Administrator rights are required to uninstall programs." + Environment.NewLine + Environment.NewLine +
                "Close the application, then start it with \"Run as administrator\".",
                MessageResult.Ok);
            _viewModel.SetStatusMessage("Administrator rights are required to uninstall programs");
            return false;
        }

        private List<ProgramEntry> ConfirmRunning(IReadOnlyList<ProgramEntry> programs)
        {
            var snapshot = ProcessService.BatchFindRunning(programs);
            var ready = new List<ProgramEntry>();

            foreach (var program in programs)
            {
                if (!snapshot.TryGetValue(program.Key, out var entries) || entries.Count == 0)
                {
                    ready.Add(program);
                    continue;
                }

                var listing = string.Join(
                    Environment.NewLine,
                    entries.Take(10).Select(entry => "PID " + entry.Pid + "  -  " + entry.Name));

                var answer = MessageDialog.Show(
                    _owner,
                    "Program is running",
                    program.Name + " is currently running:" + Environment.NewLine + Environment.NewLine +
                    listing + Environment.NewLine + Environment.NewLine +
                    "Terminate it and continue?",
                    MessageResult.Yes,
                    MessageResult.No,
                    MessageResult.Cancel);

                if (answer == MessageResult.Cancel)
                {
                    return null;
                }

                if (answer == MessageResult.No)
                {
                    Log.Info("Skipped " + program.Name + " because it is running");
                    continue;
                }

                var (_, errors) = ProcessService.KillProcesses(entries);
                var remaining = ProcessService.FindRunning(program);
                if (remaining.Count > 0)
                {
                    var details = string.Join("; ", errors.Take(3));
                    MessageDialog.Show(
                        _owner,
                        "Could not terminate",
                        program.Name + " is still running and will be skipped." + Environment.NewLine + details,
                        MessageResult.Ok);
                    continue;
                }

                ready.Add(program);
            }

            return ready;
        }
    }
}
