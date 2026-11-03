using System;
using System.ComponentModel;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using UninstallerTool.Core;
using UninstallerTool.Infrastructure;
using UninstallerTool.Models;

namespace UninstallerTool.Views.Dialogs
{
    public partial class FilePreviewDialog : Window
    {
        private const int PreviewLimit = 5000;

        private readonly ProgramEntry _program;
        private CancellationTokenSource _scan;
        private bool _closing;

        public FilePreviewDialog(ProgramEntry program)
        {
            InitializeComponent();
            _program = program;
            Title = "Folder preview \u2014 " + program.Name;
            Loaded += (sender, args) => StartScan();
            Closing += OnClosing;
        }

        private async void StartScan()
        {
            _scan = new CancellationTokenSource();
            var token = _scan.Token;

            FileScan result;
            try
            {
                result = await Task.Factory.StartNew(
                    () => FileSystemService.ScanProgramFiles(_program, PreviewLimit, () => token.IsCancellationRequested),
                    token);
            }
            catch (OperationCanceledException)
            {
                return;
            }
            catch (Exception exception)
            {
                Log.Exception("Folder scan failed", exception);
                LoadingLabel.Text = "Could not scan the folder: " + exception.Message;
                LoadingLabel.Visibility = Visibility.Visible;
                CancelButton.IsEnabled = false;
                CloseButton.IsEnabled = true;
                return;
            }

            if (_closing)
            {
                return;
            }

            ShowResult(result);
        }

        private void ShowResult(FileScan result)
        {
            LoadingLabel.Visibility = Visibility.Collapsed;

            if (result.Files.Count > 0)
            {
                FileList.Visibility = Visibility.Visible;
                foreach (var file in result.Files)
                {
                    FileList.Items.Add(new TextBlock
                    {
                        Text = file.Path + "   \u00b7   " + Formatting.FormatSize(file.Size),
                        TextTrimming = TextTrimming.CharacterEllipsis,
                        ToolTip = file.Path
                    });
                }

                if (result.Truncated)
                {
                    FileList.Items.Add(new TextBlock
                    {
                        Text = "\u2026 showing the " + PreviewLimit + " largest files of " + result.TotalCount,
                        Foreground = (System.Windows.Media.Brush)FindResource("TextTertiaryBrush")
                    });
                }
            }
            else
            {
                LoadingLabel.Text = "No safe program folder was found to preview";
                LoadingLabel.Visibility = Visibility.Visible;
            }

            CountLabel.Text = "Files found: " + result.TotalCount;
            SizeLabel.Text = "Total size: " + Formatting.FormatSize(result.TotalSize);

            if (result.Cancelled)
            {
                LoadingLabel.Text = "Scan stopped early";
                LoadingLabel.Visibility = Visibility.Visible;
            }

            CancelButton.IsEnabled = false;
            CloseButton.IsEnabled = true;
        }

        private void OnCancelClick(object sender, RoutedEventArgs e)
        {
            try
            {
                _scan?.Cancel();
            }
            catch (ObjectDisposedException)
            {
            }

            LoadingLabel.Text = "Stopping the scan…";
            LoadingLabel.Visibility = Visibility.Visible;
            CancelButton.IsEnabled = false;
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
                _scan?.Cancel();
            }
            catch (ObjectDisposedException)
            {
            }
        }
    }
}
