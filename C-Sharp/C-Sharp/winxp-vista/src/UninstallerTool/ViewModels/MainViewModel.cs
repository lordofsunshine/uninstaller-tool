using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using UninstallerTool.Core;
using UninstallerTool.Infrastructure;
using UninstallerTool.Models;

namespace UninstallerTool.ViewModels
{
    public sealed class MainViewModel : ViewModelBase
    {
        private readonly List<ProgramEntry> _registry = new List<ProgramEntry>();
        private readonly List<ProgramEntry> _store = new List<ProgramEntry>();
        private readonly List<ProgramEntry> _combined = new List<ProgramEntry>();
        private readonly HashSet<ProgramEntry> _subscribed = new HashSet<ProgramEntry>();
        private CancellationTokenSource _loading;

        private string _searchText = string.Empty;
        private int _sortMode;
        private bool _isLoading;
        private bool _isBusy;
        private bool _isStoreLoading;
        private string _subtitle = "Loading installed programs\u2026";
        private string _summaryBold = string.Empty;
        private string _summaryRest = "Loading installed programs\u2026";
        private string _statusOverride;
        private bool _loadFailed;
        private bool _progressVisible;
        private bool _progressIndeterminate;
        private int _progressValue;
        private int _progressMaximum = 1;

        public MainViewModel()
        {
            Programs = new ObservableCollection<ProgramEntry>();
        }

        public ObservableCollection<ProgramEntry> Programs { get; }

        public string SearchText
        {
            get => _searchText;
            set
            {
                if (Set(ref _searchText, value ?? string.Empty))
                {
                    ApplyView();
                    UpdateSubtitle();
                }
            }
        }

        public int SortMode
        {
            get => _sortMode;
            set
            {
                if (Set(ref _sortMode, value))
                {
                    ApplyView();
                    UpdateSubtitle();
                }
            }
        }

        public bool IsLoading
        {
            get => _isLoading;
            private set
            {
                if (Set(ref _isLoading, value))
                {
                    UpdateProgressVisibility();
                }
            }
        }

        public bool IsBusy
        {
            get => _isBusy;
            private set
            {
                if (Set(ref _isBusy, value))
                {
                    UpdateProgressVisibility();
                    UpdateSummary();
                }
            }
        }

        public bool IsStoreLoading
        {
            get => _isStoreLoading;
            private set
            {
                if (Set(ref _isStoreLoading, value))
                {
                    UpdateProgressVisibility();
                    UpdateSubtitle();
                }
            }
        }

        public string Subtitle
        {
            get => _subtitle;
            private set => Set(ref _subtitle, value);
        }

        public string SummaryBold
        {
            get => _summaryBold;
            private set => Set(ref _summaryBold, value);
        }

        public string SummaryRest
        {
            get => _summaryRest;
            private set => Set(ref _summaryRest, value);
        }

        public bool ProgressVisible
        {
            get => _progressVisible;
            private set => Set(ref _progressVisible, value);
        }

        public bool ProgressIndeterminate
        {
            get => _progressIndeterminate;
            private set => Set(ref _progressIndeterminate, value);
        }

        public int ProgressValue
        {
            get => _progressValue;
            private set => Set(ref _progressValue, value);
        }

        public int ProgressMaximum
        {
            get => _progressMaximum;
            private set => Set(ref _progressMaximum, value);
        }

        public int TotalCount => _combined.Count;

        public int ShownCount => Programs.Count;

        public long TotalSize => _combined.Sum(item => item.SizeBytes);

        public bool LoadFailed => _loadFailed;

        public IList<ProgramEntry> CheckedPrograms =>
            _combined.Where(item => item.Checked).ToList();

        public HashSet<string> CheckedKeys()
        {
            return new HashSet<string>(
                _combined.Where(item => item.Checked).Select(item => item.Key),
                StringComparer.Ordinal);
        }

        public ProgramEntry FindByKey(string key)
        {
            if (string.IsNullOrEmpty(key))
            {
                return null;
            }

            return _combined.FirstOrDefault(item => item.Key == key);
        }

        public async Task LoadAsync(bool forceStore = false)
        {
            if (IsLoading)
            {
                return;
            }

            var checkedKeys = CheckedKeys();
            _loadFailed = false;
            _statusOverride = null;
            IsLoading = true;
            IsStoreLoading = false;
            Subtitle = "Reading the registry\u2026";
            SummaryBold = string.Empty;
            SummaryRest = "Loading installed programs\u2026";
            _registry.Clear();
            _store.Clear();
            Rebuild(string.Empty);

            _loading = new CancellationTokenSource();
            var token = _loading.Token;

            try
            {
                await ProgramLoader.LoadAsync(OnRegistryLoaded, OnStoreLoaded, token, forceStore).ConfigureAwait(true);
            }
            catch (OperationCanceledException)
            {
            }
            catch (Exception exception)
            {
                Log.Exception("Program loading failed", exception);
                _loadFailed = true;
                Subtitle = "Could not load installed programs";
                SummaryBold = string.Empty;
                SummaryRest = "Registry error";
            }
            finally
            {
                IsLoading = false;
                IsStoreLoading = false;
                _loading?.Dispose();
                _loading = null;
                if (!_loadFailed)
                {
                    RestoreChecked(checkedKeys);
                    UpdateSubtitle();
                    UpdateSummary();
                }
            }
        }

        public void CancelLoading()
        {
            try
            {
                _loading?.Cancel();
            }
            catch (ObjectDisposedException)
            {
            }
        }

        public void RestoreChecked(IEnumerable<string> keys)
        {
            var wanted = new HashSet<string>(keys ?? Enumerable.Empty<string>(), StringComparer.Ordinal);
            foreach (var program in _combined)
            {
                program.Checked = wanted.Contains(program.Key);
            }

            UpdateSummary();
        }

        public void SetBusy(bool busy)
        {
            IsBusy = busy;
        }

        public void SetStatus(string key, ProgramStatus status)
        {
            if (string.IsNullOrEmpty(key))
            {
                return;
            }

            var program = FindByKey(key);
            if (program != null)
            {
                program.Status = status;
            }
        }

        public void SetProgress(bool visible, bool indeterminate, int value, int maximum)
        {
            ProgressVisible = visible;
            ProgressIndeterminate = indeterminate;
            ProgressMaximum = Math.Max(1, maximum);
            ProgressValue = Math.Max(0, Math.Min(value, ProgressMaximum));
        }

        public void SetStatusMessage(string message)
        {
            _statusOverride = message;
            if (string.IsNullOrEmpty(message))
            {
                UpdateSummary();
                return;
            }

            SummaryBold = string.Empty;
            SummaryRest = message;
        }

        public void AppendStatusMessage(string suffix)
        {
            if (string.IsNullOrEmpty(suffix))
            {
                if (!string.IsNullOrEmpty(_statusOverride))
                {
                    SummaryBold = string.Empty;
                    SummaryRest = _statusOverride;
                }

                return;
            }

            var baseText = string.IsNullOrEmpty(_statusOverride) ? "Uninstalling" : _statusOverride;
            SummaryBold = string.Empty;
            SummaryRest = baseText + "   |   " + suffix;
        }

        public void UpdateSummary()
        {
            if (!string.IsNullOrEmpty(_statusOverride))
            {
                return;
            }

            if (IsLoading || IsBusy)
            {
                return;
            }

            var summary = BuildDefaultSummary();
            SummaryBold = summary.Bold;
            SummaryRest = summary.Detail;
        }

        public void UpdateSubtitle()
        {
            if (_loadFailed)
            {
                return;
            }

            if (IsLoading && _combined.Count == 0)
            {
                Subtitle = "Reading the registry\u2026";
                return;
            }

            var total = _combined.Count;
            if (IsStoreLoading && total > 0)
            {
                Subtitle = total + " programs found   \u00b7   loading Store apps\u2026";
                return;
            }

            if (total == 0)
            {
                Subtitle = "No programs found";
                return;
            }

            if (_searchText.Trim().Length > 0)
            {
                Subtitle = Programs.Count + " of " + total + " programs shown";
                return;
            }

            var size = TotalSize;
            Subtitle = size > 0
                ? total + " programs found   \u00b7   " + Formatting.FormatSize(size) + " installed"
                : total + " programs found";
        }

        private void OnRegistryLoaded(IList<ProgramEntry> programs)
        {
            var application = System.Windows.Application.Current;
            if (application != null && !application.Dispatcher.CheckAccess())
            {
                application.Dispatcher.Invoke(() => OnRegistryLoaded(programs));
                return;
            }

            var checkedKeys = CheckedKeys();
            _registry.Clear();
            _registry.AddRange(programs);
            IsLoading = false;
            IsStoreLoading = true;
            Rebuild(checkedKeys);
            UpdateSubtitle();
            UpdateSummary();
        }

        private void OnStoreLoaded(IList<ProgramEntry> programs)
        {
            var application = System.Windows.Application.Current;
            if (application != null && !application.Dispatcher.CheckAccess())
            {
                application.Dispatcher.Invoke(() => OnStoreLoaded(programs));
                return;
            }

            var checkedKeys = CheckedKeys();
            _store.Clear();
            _store.AddRange(programs);
            Rebuild(checkedKeys);
            UpdateSubtitle();
            UpdateSummary();
        }

        private void Rebuild(IEnumerable<string> checkedKeys)
        {
            var previous = checkedKeys as HashSet<string> ?? new HashSet<string>(checkedKeys ?? Enumerable.Empty<string>(), StringComparer.Ordinal);
            var seen = new HashSet<string>(StringComparer.Ordinal);
            _combined.Clear();

            foreach (var program in _registry.Concat(_store))
            {
                if (!seen.Add(program.Key))
                {
                    continue;
                }

                program.Checked = previous.Contains(program.Key);
                _combined.Add(program);
                Subscribe(program);
            }

            if (previous.Count > 0)
            {
                foreach (var program in _combined)
                {
                    program.Checked = previous.Contains(program.Key);
                }
            }

            _combined.Sort((left, right) => string.Compare(left.Name, right.Name, StringComparison.OrdinalIgnoreCase));
            ApplyView();
            UpdateSummary();
        }

        private void Rebuild(string newSelection)
        {
            _ = newSelection;
            Rebuild(Enumerable.Empty<string>());
        }

        private void Subscribe(ProgramEntry program)
        {
            if (!_subscribed.Add(program))
            {
                return;
            }

            program.PropertyChanged += OnProgramChanged;
        }

        private void OnProgramChanged(object sender, PropertyChangedEventArgs args)
        {
            if (args.PropertyName == nameof(ProgramEntry.Checked))
            {
                UpdateSummary();
            }
        }

        private void ApplyView()
        {
            var query = _searchText.Trim().ToLowerInvariant();
            IEnumerable<ProgramEntry> items = _combined;

            if (query.Length > 0)
            {
                items = items.Where(item =>
                    (item.Name + " " + item.Publisher + " " + item.Version).ToLowerInvariant().Contains(query));
            }

            switch (_sortMode)
            {
                case 1:
                    items = items
                        .OrderByDescending(item => item.SizeKb)
                        .ThenBy(item => item.Name, StringComparer.OrdinalIgnoreCase);
                    break;
                case 2:
                    items = items
                        .OrderByDescending(item => item.InstallDate, StringComparer.OrdinalIgnoreCase)
                        .ThenBy(item => item.Name, StringComparer.OrdinalIgnoreCase);
                    break;
                case 3:
                    items = items
                        .OrderBy(item => item.Publisher, StringComparer.OrdinalIgnoreCase)
                        .ThenBy(item => item.Name, StringComparer.OrdinalIgnoreCase);
                    break;
                default:
                    items = items.OrderBy(item => item.Name, StringComparer.OrdinalIgnoreCase);
                    break;
            }

            Programs.Clear();
            foreach (var item in items)
            {
                Programs.Add(item);
            }
        }

        internal sealed class SummaryText
        {
            public SummaryText(string bold, string detail)
            {
                Bold = bold;
                Detail = detail;
            }

            public string Bold { get; }

            public string Detail { get; }
        }

        private SummaryText BuildDefaultSummary()
        {
            var checkedPrograms = CheckedPrograms;
            if (checkedPrograms.Count == 0)
            {
                return new SummaryText(string.Empty, "No programs selected");
            }

            var size = checkedPrograms.Sum(item => item.SizeBytes);
            var rest = size > 0
                ? "selected   \u00b7   ~" + Formatting.FormatSize(size) + " to be freed"
                : "selected";
            return new SummaryText(checkedPrograms.Count.ToString(), rest);
        }

        private void UpdateProgressVisibility()
        {
            ProgressVisible = IsLoading || IsStoreLoading || IsBusy;
            if (!IsBusy)
            {
                ProgressIndeterminate = IsLoading || IsStoreLoading;
            }
        }
    }
}
