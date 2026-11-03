using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using UninstallerTool.Core;
using UninstallerTool.Infrastructure;
using UninstallerTool.Models;
using UninstallerTool.Theme;
using UninstallerTool.ViewModels;

namespace UninstallerTool.Views.Dialogs
{
    public sealed class LeftoverItem : ViewModelBase
    {
        private bool _isChecked = true;

        public LeftoverItem(string text, RegistryEntry entry = null)
        {
            Text = text ?? string.Empty;
            Entry = entry;
        }

        public string Text { get; }

        public RegistryEntry Entry { get; }

        public bool IsChecked
        {
            get => _isChecked;
            set => Set(ref _isChecked, value);
        }
    }

    public partial class LeftoversDialog : Window
    {
        private readonly Leftovers _leftovers;
        private readonly List<LeftoverItem> _fileItems = new List<LeftoverItem>();
        private readonly List<LeftoverItem> _registryItems = new List<LeftoverItem>();
        private bool _busy;

        public LeftoversDialog(Leftovers leftovers)
        {
            InitializeComponent();
            _leftovers = leftovers;

            foreach (var file in leftovers.Files)
            {
                _fileItems.Add(new LeftoverItem(file));
            }

            foreach (var entry in leftovers.Registry)
            {
                _registryItems.Add(new LeftoverItem(entry.Path, entry));
            }

            BuildSection("Files (" + ItemCount(_fileItems.Count) + ")", _fileItems);
            BuildSection("Registry entries (" + ItemCount(_registryItems.Count) + ")", _registryItems);
            UpdateRemoveButton();
        }

        private static string ItemCount(int count)
        {
            return count == 1 ? "1 item" : count + " items";
        }

        private void BuildSection(string caption, List<LeftoverItem> items)
        {
            if (items.Count == 0)
            {
                return;
            }

            Sections.Children.Add(new TextBlock
            {
                Text = caption,
                FontSize = 12,
                FontWeight = FontWeights.SemiBold,
                Foreground = (Brush)FindResource(ThemeManager.PrimaryBrushKey),
                Margin = new Thickness(0, 0, 0, 6)
            });

            var list = new ListBox
            {
                Style = (Style)FindResource("ListPanel"),
                ItemTemplate = (DataTemplate)FindResource("LeftoverRow"),
                Height = Math.Min(220, Math.Max(84, items.Count * 34 + 10)),
                Margin = new Thickness(0, 0, 0, 12),
                ItemsSource = items
            };

            foreach (var item in items)
            {
                item.PropertyChanged += (sender, args) =>
                {
                    if (args.PropertyName == nameof(LeftoverItem.IsChecked))
                    {
                        UpdateRemoveButton();
                    }
                };
            }

            Sections.Children.Add(list);
        }

        private void UpdateRemoveButton()
        {
            RemoveButton.IsEnabled = !_busy && SelectedFiles().Count + SelectedRegistry().Count > 0;
        }

        private List<string> SelectedFiles()
        {
            return _fileItems.Where(item => item.IsChecked).Select(item => item.Text).ToList();
        }

        private List<RegistryEntry> SelectedRegistry()
        {
            return _registryItems.Where(item => item.IsChecked).Select(item => item.Entry).ToList();
        }

        private async void OnRemoveClick(object sender, RoutedEventArgs e)
        {
            if (_busy)
            {
                return;
            }

            var files = SelectedFiles();
            var registry = SelectedRegistry();
            if (files.Count == 0 && registry.Count == 0)
            {
                DialogResult = false;
                Close();
                return;
            }

            var selection = new Leftovers
            {
                ProgramKey = _leftovers.ProgramKey,
                ProgramName = _leftovers.ProgramName,
                Files = files,
                Registry = registry
            };

            SetBusy(true);
            RemovalResult result;
            try
            {
                result = await Task.Run(() => RemovalService.RemoveLeftovers(selection));
            }
            catch (Exception exception)
            {
                Log.Exception("Cleanup failed", exception);
                SetBusy(false);
                MessageDialog.Show(
                    this,
                    "Cleanup failed",
                    "Could not complete cleanup:" + Environment.NewLine + exception.Message,
                    MessageResult.Ok);
                return;
            }

            ReportResult(result);
            DialogResult = true;
            Close();
        }

        private void ReportResult(RemovalResult result)
        {
            var summary = "Removed locations: " + result.RemovedFiles + Environment.NewLine +
                          "Registry entries: " + result.RemovedRegistry;

            if (result.ScheduledFiles > 0)
            {
                summary += Environment.NewLine +
                           "Locked items scheduled after restart: " + result.ScheduledFiles + Environment.NewLine +
                           "Please restart Windows to finish removal.";
            }

            if (result.Backups.Count > 0)
            {
                var folder = Path.GetDirectoryName(result.Backups[0]) ?? string.Empty;
                summary += Environment.NewLine + "Registry backups: " + result.Backups.Count + " file(s) in " + folder;
            }

            if (result.Errors.Count > 0)
            {
                var details = string.Join(Environment.NewLine, result.Errors.Take(5));
                if (result.Errors.Count > 5)
                {
                    details += Environment.NewLine + "… and " + (result.Errors.Count - 5) + " more";
                }

                MessageDialog.Show(
                    this,
                    "Cleanup completed with errors",
                    summary + Environment.NewLine + Environment.NewLine + details,
                    MessageResult.Ok);
                return;
            }

            MessageDialog.Show(this, "Cleanup completed", summary, MessageResult.Ok);
        }

        private void SetBusy(bool busy)
        {
            _busy = busy;
            TitleLabel.Text = busy ? "Removing leftover items…" : "Found leftover items:";
            CancelButton.IsEnabled = !busy;
            RemoveButton.IsEnabled = !busy && SelectedFiles().Count + SelectedRegistry().Count > 0;
        }

        private void OnCancelClick(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }
    }
}
