using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Threading;
using UninstallerTool.Infrastructure;
using UninstallerTool.Models;
using UninstallerTool.Services;
using UninstallerTool.Theme;
using UninstallerTool.ViewModels;
using UninstallerTool.Views.Dialogs;

namespace UninstallerTool.Views
{
    public partial class MainWindow : Window
    {
        private const int SearchDelayMilliseconds = 160;
        private const int RefreshDelayMilliseconds = 2000;

        private readonly DispatcherTimer _searchTimer;
        private readonly AppSettings _settings;
        private bool _suppressUiEvents;
        private bool _closing;
        private string _selectedKey = string.Empty;
        private UninstallWorkflow _workflow;

        public MainWindow()
        {
            InitializeComponent();

            _settings = new AppSettings();
            ViewModel = new MainViewModel();
            DataContext = ViewModel;

            var assembly = typeof(MainWindow).Assembly.GetName().Version;
            VersionText.Text = "v" + (assembly?.ToString(3) ?? "1.0.0");

            _searchTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(SearchDelayMilliseconds) };
            _searchTimer.Tick += OnSearchTimerTick;

            _suppressUiEvents = true;
            SortCombo.SelectedIndex = Math.Max(0, Math.Min(3, _settings.SortMode));
            SilentCheck.IsChecked = _settings.SilentMode;
            _suppressUiEvents = false;
            ViewModel.SortMode = SortCombo.SelectedIndex;

            ProgramList.ItemsSource = ViewModel.Programs;
            Details.PreviewRequested += (sender, args) => ShowFilePreview();
            Details.InfoRequested += (sender, args) => ShowSelectedInfo();
            ViewModel.PropertyChanged += OnViewModelPropertyChanged;

            Loaded += OnLoaded;
            Closing += OnClosing;
            ThemeManager.ThemeChanged += OnThemeChanged;
        }

        public MainViewModel ViewModel { get; }

        private void OnLoaded(object sender, RoutedEventArgs e)
        {
            RestoreWindowSettings();
            WindowSizing.Fit(this);
            _ = RefreshAsync();
        }

        private async System.Threading.Tasks.Task RefreshAsync(bool forceStore = false)
        {
            if (ViewModel.IsLoading || ViewModel.IsBusy)
            {
                return;
            }

            var previousKey = _selectedKey;
            var scroll = FindScrollViewer(ProgramList)?.VerticalOffset ?? 0;
            _selectedKey = string.Empty;
            Details.SetProgram(null);

            await ViewModel.LoadAsync(forceStore);

            if (previousKey.Length > 0)
            {
                var restored = ViewModel.FindByKey(previousKey);
                if (restored != null && ViewModel.Programs.Contains(restored))
                {
                    ProgramList.SelectedItem = restored;
                    ProgramList.ScrollIntoView(restored);
                }
            }

            var viewer = FindScrollViewer(ProgramList);
            if (viewer != null && scroll > 0)
            {
                viewer.ScrollToVerticalOffset(scroll);
            }

            UpdateButtonStates();
        }

        private void RestoreWindowSettings()
        {
            if (_settings.WindowWidth.HasValue && _settings.WindowHeight.HasValue &&
                _settings.WindowLeft.HasValue && _settings.WindowTop.HasValue)
            {
                Width = Math.Max(MinWidth, _settings.WindowWidth.Value);
                Height = Math.Max(MinHeight, _settings.WindowHeight.Value);
                Left = _settings.WindowLeft.Value;
                Top = _settings.WindowTop.Value;
            }

            if (_settings.WindowMaximized)
            {
                WindowState = WindowState.Maximized;
            }

            if (_settings.SplitterRatio > 0.05 && _settings.SplitterRatio < 0.95)
            {
                ListColumn.Width = new GridLength(1 - _settings.SplitterRatio, GridUnitType.Star);
                DetailsColumn.Width = new GridLength(_settings.SplitterRatio, GridUnitType.Star);
            }
        }

        private void SaveWindowSettings()
        {
            if (WindowState == WindowState.Normal)
            {
                _settings.WindowLeft = Left;
                _settings.WindowTop = Top;
                _settings.WindowWidth = Width;
                _settings.WindowHeight = Height;
            }

            _settings.WindowMaximized = WindowState == WindowState.Maximized;
            var total = Math.Max(1, DetailsColumn.ActualWidth + ListColumn.ActualWidth);
            _settings.SplitterRatio = Math.Max(0.05, Math.Min(0.95, DetailsColumn.ActualWidth / total));
            _settings.SortMode = SortCombo.SelectedIndex;
            _settings.SilentMode = SilentCheck.IsChecked == true;
            _settings.Save();
        }

        private void OnViewModelPropertyChanged(object sender, PropertyChangedEventArgs e)
        {
            switch (e.PropertyName)
            {
                case nameof(MainViewModel.SummaryBold):
                case nameof(MainViewModel.SummaryRest):
                    RenderSummary();
                    break;
                case nameof(MainViewModel.IsBusy):
                case nameof(MainViewModel.IsLoading):
                case nameof(MainViewModel.IsStoreLoading):
                    UpdateButtonStates();
                    break;
                case nameof(MainViewModel.ProgressVisible):
                    Progress.Visibility = ViewModel.ProgressVisible ? Visibility.Visible : Visibility.Collapsed;
                    break;
            }
        }

        private void RenderSummary()
        {
            SummaryText.Inlines.Clear();
            if (ViewModel.SummaryBold.Length > 0)
            {
                SummaryText.Inlines.Add(new Run(ViewModel.SummaryBold)
                {
                    FontWeight = FontWeights.Bold,
                    Foreground = (Brush)FindResource(ThemeManager.TextBrushKey)
                });
                SummaryText.Inlines.Add(new Run(" " + ViewModel.SummaryRest));
                return;
            }

            SummaryText.Inlines.Add(new Run(ViewModel.SummaryRest));
        }

        private void UpdateButtonStates()
        {
            var idle = !ViewModel.IsLoading && !ViewModel.IsBusy;
            RefreshButton.IsEnabled = idle;
            DiskButton.IsEnabled = idle;
            SortCombo.IsEnabled = idle;
            SilentCheck.IsEnabled = !ViewModel.IsBusy;
            UninstallButton.IsEnabled = idle;
            ProgramList.IsEnabled = !ViewModel.IsBusy;
        }

        private void OnSearchTextChanged(object sender, TextChangedEventArgs e)
        {
            var text = SearchBox.Text ?? string.Empty;
            SearchPlaceholder.Visibility = text.Length == 0 ? Visibility.Visible : Visibility.Collapsed;
            ClearSearchButton.Visibility = text.Length == 0 ? Visibility.Collapsed : Visibility.Visible;
            _searchTimer.Stop();
            _searchTimer.Start();
        }

        private void OnSearchTimerTick(object sender, EventArgs e)
        {
            _searchTimer.Stop();
            ViewModel.SearchText = SearchBox.Text;
            KeepSelectionVisible();
        }

        private void KeepSelectionVisible()
        {
            if (_selectedKey.Length == 0)
            {
                return;
            }

            var current = ViewModel.FindByKey(_selectedKey);
            if (current != null && ViewModel.Programs.Contains(current))
            {
                if (!ReferenceEquals(ProgramList.SelectedItem, current))
                {
                    ProgramList.SelectedItem = current;
                }

                return;
            }

            ProgramList.SelectedItem = null;
            Details.SetProgram(null);
            _selectedKey = string.Empty;
        }

        private void OnClearSearchClick(object sender, RoutedEventArgs e)
        {
            SearchBox.Text = string.Empty;
            SearchBox.Focus();
        }

        private void OnSortChanged(object sender, SelectionChangedEventArgs e)
        {
            if (_suppressUiEvents || ViewModel == null)
            {
                return;
            }

            ViewModel.SortMode = Math.Max(0, SortCombo.SelectedIndex);
            _settings.SortMode = ViewModel.SortMode;
            KeepSelectionVisible();

            var selected = ProgramList.SelectedItem as ProgramEntry;
            if (selected != null)
            {
                ProgramList.ScrollIntoView(selected);
            }
        }

        private void OnSilentChanged(object sender, RoutedEventArgs e)
        {
            if (_suppressUiEvents)
            {
                return;
            }

            _settings.SilentMode = SilentCheck.IsChecked == true;
        }

        private void OnSelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            var program = ProgramList.SelectedItem as ProgramEntry;
            _selectedKey = program?.Key ?? string.Empty;
            Details.SetProgram(program);
        }

        private void OnProgramListKeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key == Key.Space)
            {
                var program = ProgramList.SelectedItem as ProgramEntry;
                if (program != null && !ViewModel.IsBusy)
                {
                    program.Checked = !program.Checked;
                }

                e.Handled = true;
                return;
            }

            if (e.Key == Key.Delete)
            {
                _ = UninstallAsync();
                e.Handled = true;
                return;
            }

            if (e.Key == Key.Enter || e.Key == Key.Return)
            {
                ShowSelectedInfo();
                e.Handled = true;
            }
        }

        protected override void OnPreviewKeyDown(KeyEventArgs e)
        {
            base.OnPreviewKeyDown(e);

            if (e.Key == Key.F5)
            {
                _ = RefreshAsync();
                e.Handled = true;
                return;
            }

            if (e.Key == Key.F && (Keyboard.Modifiers & ModifierKeys.Control) == ModifierKeys.Control)
            {
                SearchBox.Focus();
                SearchBox.SelectAll();
                e.Handled = true;
                return;
            }

            if (e.Key == Key.U && (Keyboard.Modifiers & ModifierKeys.Control) == ModifierKeys.Control)
            {
                _ = UninstallAsync();
                e.Handled = true;
            }
        }

        private async void OnRefreshClick(object sender, RoutedEventArgs e)
        {
            await RefreshAsync();
        }

        private async void OnUninstallClick(object sender, RoutedEventArgs e)
        {
            await UninstallAsync();
        }

        private async System.Threading.Tasks.Task UninstallAsync()
        {
            if (ViewModel.IsLoading || ViewModel.IsBusy)
            {
                return;
            }

            var programs = ViewModel.CheckedPrograms;
            if (programs.Count == 0)
            {
                MessageDialog.Show(this, "Nothing selected", "Select at least one program to uninstall.", MessageResult.Ok);
                return;
            }

            var message = programs.Count == 1
                ? "Are you sure you want to uninstall " + programs[0].Name + "?"
                : "Are you sure you want to uninstall " + programs.Count + " selected programs?";

            if (!MessageDialog.Confirm(this, "Confirmation", message))
            {
                return;
            }

            _workflow = new UninstallWorkflow(this, ViewModel);
            var removed = await _workflow.RunAsync(programs, SilentCheck.IsChecked == true);
            UpdateButtonStates();

            if (removed)
            {
                await System.Threading.Tasks.Task.Delay(RefreshDelayMilliseconds);
                await RefreshAsync(forceStore: true);
            }
        }

        private void OnDiskUsageClick(object sender, RoutedEventArgs e)
        {
            if (ViewModel.IsBusy || ViewModel.IsLoading)
            {
                return;
            }

            var dialog = new DiskSpaceDialog(ViewModel.Programs.ToList()) { Owner = this };
            dialog.ShowDialog();
        }

        private void ShowSelectedInfo()
        {
            var program = Details.Program ?? ProgramList.SelectedItem as ProgramEntry;
            if (program == null)
            {
                return;
            }

            var dialog = new InfoDialog(program) { Owner = this };
            dialog.ShowDialog();
        }

        private void ShowFilePreview()
        {
            var program = Details.Program;
            if (program == null)
            {
                var checkedPrograms = ViewModel.CheckedPrograms;
                if (checkedPrograms.Count == 0)
                {
                    MessageDialog.Show(this, "No program selected", "Select a program first.", MessageResult.Ok);
                    return;
                }

                program = checkedPrograms[0];
            }

            var dialog = new FilePreviewDialog(program) { Owner = this };
            dialog.ShowDialog();
        }

        private void OnProgramListRightButtonDown(object sender, MouseButtonEventArgs e)
        {
            var item = ItemsControl.ContainerFromElement(ProgramList, (DependencyObject)e.OriginalSource) as ListBoxItem;
            if (item != null)
            {
                item.IsSelected = true;
                item.Focus();
            }
        }

        private void OnMenuInfoClick(object sender, RoutedEventArgs e)
        {
            ShowSelectedInfo();
        }

        private void OnMenuPreviewClick(object sender, RoutedEventArgs e)
        {
            var program = ProgramList.SelectedItem as ProgramEntry;
            if (program == null)
            {
                return;
            }

            var dialog = new FilePreviewDialog(program) { Owner = this };
            dialog.ShowDialog();
        }

        private async void OnMenuUninstallClick(object sender, RoutedEventArgs e)
        {
            var program = ProgramList.SelectedItem as ProgramEntry;
            if (program == null || ViewModel.IsBusy || ViewModel.IsLoading)
            {
                return;
            }

            if (!MessageDialog.Confirm(this, "Confirmation", "Are you sure you want to uninstall " + program.Name + "?"))
            {
                return;
            }

            _workflow = new UninstallWorkflow(this, ViewModel);
            var removed = await _workflow.RunAsync(new List<ProgramEntry> { program }, SilentCheck.IsChecked == true);
            UpdateButtonStates();

            if (removed)
            {
                await System.Threading.Tasks.Task.Delay(RefreshDelayMilliseconds);
                await RefreshAsync(forceStore: true);
            }
        }

        private void OnThemeChanged(object sender, EventArgs e)
        {
            RenderSummary();
        }

        private void OnClosing(object sender, CancelEventArgs e)
        {
            if (_closing)
            {
                return;
            }

            if (ViewModel.IsBusy)
            {
                e.Cancel = true;
                ViewModel.SetStatusMessage("Cleaning up \u2014 the window will close when the operation finishes");
                return;
            }

            _closing = true;
            ViewModel.CancelLoading();
            SaveWindowSettings();
            ThemeManager.ThemeChanged -= OnThemeChanged;
        }

        private static ScrollViewer FindScrollViewer(DependencyObject root)
        {
            if (root is ScrollViewer viewer)
            {
                return viewer;
            }

            for (var index = 0; index < VisualTreeHelper.GetChildrenCount(root); index++)
            {
                var found = FindScrollViewer(VisualTreeHelper.GetChild(root, index));
                if (found != null)
                {
                    return found;
                }
            }

            return null;
        }
    }
}
