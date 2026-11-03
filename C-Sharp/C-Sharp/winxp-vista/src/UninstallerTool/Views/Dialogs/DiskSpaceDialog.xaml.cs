using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using UninstallerTool.Core;
using UninstallerTool.Infrastructure;
using UninstallerTool.Models;
using UninstallerTool.Theme;

namespace UninstallerTool.Views.Dialogs
{
    public partial class DiskSpaceDialog : Window
    {
        private readonly List<ProgramEntry> _programs;
        private readonly Dictionary<string, long> _sizes;
        private readonly HashSet<string> _measured = new HashSet<string>(StringComparer.Ordinal);
        private CancellationTokenSource _measurement;
        private bool _closing;

        public DiskSpaceDialog(IList<ProgramEntry> programs)
        {
            InitializeComponent();
            _programs = programs.ToList();
            _sizes = _programs.ToDictionary(item => item.Key, item => item.SizeBytes, StringComparer.Ordinal);

            BuildStatCards();
            RefreshLists();

            Loaded += (sender, args) => StartMeasurement();
            Closing += OnClosing;
        }

        private void BuildStatCards()
        {
            var total = _sizes.Values.Sum();
            var unknown = _programs.Count(item => item.SizeBytes == 0);

            AddCard("Total size", total > 0 ? Formatting.FormatSize(total) : "Unknown");
            AddCard("Programs", _programs.Count.ToString());
            if (unknown > 0)
            {
                AddCard("No size info", unknown.ToString());
            }
        }

        private void AddCard(string caption, string value)
        {
            var card = new Border
            {
                Background = (Brush)FindResource(ThemeManager.SurfaceBrushKey),
                CornerRadius = new CornerRadius(14),
                Padding = new Thickness(18, 14, 18, 14),
                Margin = new Thickness(0, 0, 12, 0)
            };

            var content = new StackPanel();
            content.Children.Add(new TextBlock
            {
                Text = value,
                FontSize = 22,
                FontWeight = FontWeights.Bold,
                Foreground = (Brush)FindResource(ThemeManager.PrimaryBrushKey)
            });
            content.Children.Add(new TextBlock
            {
                Text = caption,
                FontSize = 12,
                Margin = new Thickness(0, 2, 0, 0),
                Foreground = (Brush)FindResource(ThemeManager.TextSecondaryBrushKey)
            });

            card.Child = content;
            StatRow.Children.Add(card);
        }

        private void RefreshLists()
        {
            TopList.Items.Clear();
            var ranked = _programs
                .Select(item => new { Program = item, Size = _sizes.TryGetValue(item.Key, out var size) ? size : 0 })
                .Where(item => item.Size > 0)
                .OrderByDescending(item => item.Size)
                .Take(10);

            foreach (var item in ranked)
            {
                var suffix = _measured.Contains(item.Program.Key) ? " (on disk)" : string.Empty;
                TopList.Items.Add(new TextBlock
                {
                    Text = item.Program.Name + "   \u00b7   " + Formatting.FormatSize(item.Size) + suffix,
                    TextTrimming = TextTrimming.CharacterEllipsis
                });
            }

            PublisherList.Items.Clear();
            var byPublisher = _programs
                .GroupBy(item => string.IsNullOrWhiteSpace(item.Publisher) ? "Unknown" : item.Publisher)
                .Select(group => new
                {
                    Publisher = group.Key,
                    Size = group.Sum(item => _sizes.TryGetValue(item.Key, out var size) ? size : 0)
                })
                .Where(item => item.Size > 0)
                .OrderByDescending(item => item.Size)
                .Take(10);

            foreach (var item in byPublisher)
            {
                PublisherList.Items.Add(new TextBlock
                {
                    Text = item.Publisher + "   \u00b7   " + Formatting.FormatSize(item.Size),
                    TextTrimming = TextTrimming.CharacterEllipsis
                });
            }
        }

        private async void StartMeasurement()
        {
            var cache = new SizeCache();
            var candidates = _programs
                .Where(item => item.SizeBytes == 0)
                .Where(item => !item.IsStoreApp)
                .Where(item => !string.IsNullOrWhiteSpace(item.InstallLocation))
                .Where(item => cache.Get(item.InstallLocation) == null)
                .ToList();

            if (candidates.Count == 0)
            {
                MeasureLabel.Visibility = Visibility.Collapsed;
                return;
            }

            _measurement = new CancellationTokenSource();
            var token = _measurement.Token;
            var total = candidates.Count;
            var measured = new Dictionary<string, long>(StringComparer.Ordinal);

            try
            {
                await Task.Factory.StartNew(
                    () =>
                    {
                        for (var index = 0; index < candidates.Count; index++)
                        {
                            if (token.IsCancellationRequested)
                            {
                                break;
                            }

                            var program = candidates[index];
                            var position = index;
                            Dispatcher.Invoke(() =>
                                MeasureLabel.Text = "Measuring folder sizes\u2026 " + (position + 1) + " of " + total + ": " + program.Name);

                            var size = cache.Measure(program, () => token.IsCancellationRequested);
                            if (size > 0)
                            {
                                measured[program.Key] = size;
                            }
                        }

                        cache.Save();
                    },
                    token);
            }
            catch (OperationCanceledException)
            {
                return;
            }
            catch (Exception exception)
            {
                Log.Exception("Folder size measurement failed", exception);
                MeasureLabel.Text = "Could not measure folder sizes: " + exception.Message;
                return;
            }

            if (_closing)
            {
                return;
            }

            foreach (var pair in measured)
            {
                _sizes[pair.Key] = pair.Value;
                _measured.Add(pair.Key);
            }

            RefreshLists();
            MeasureLabel.Text = _measured.Count == 0
                ? "Folder sizes are already up to date"
                : "Folder sizes measured and cached";
        }

        private void OnCloseClick(object sender, RoutedEventArgs e)
        {
            Close();
        }

        private void OnClosing(object sender, CancelEventArgs e)
        {
            _closing = true;
            try
            {
                _measurement?.Cancel();
            }
            catch (ObjectDisposedException)
            {
            }
        }
    }
}
