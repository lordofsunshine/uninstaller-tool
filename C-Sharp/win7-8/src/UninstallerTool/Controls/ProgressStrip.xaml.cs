using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media.Animation;

namespace UninstallerTool.Controls
{
    public partial class ProgressStrip : UserControl
    {
        public static readonly DependencyProperty IsIndeterminateProperty =
            DependencyProperty.Register(
                nameof(IsIndeterminate),
                typeof(bool),
                typeof(ProgressStrip),
                new PropertyMetadata(false, OnVisualStateChanged));

        public static readonly DependencyProperty ValueProperty =
            DependencyProperty.Register(
                nameof(Value),
                typeof(double),
                typeof(ProgressStrip),
                new PropertyMetadata(0d, OnVisualStateChanged));

        public static readonly DependencyProperty MaximumProperty =
            DependencyProperty.Register(
                nameof(Maximum),
                typeof(double),
                typeof(ProgressStrip),
                new PropertyMetadata(1d, OnVisualStateChanged));

        private Storyboard _storyboard;

        public ProgressStrip()
        {
            InitializeComponent();
            SizeChanged += (sender, args) => UpdateIndicator();
            Loaded += (sender, args) => UpdateIndicator();
        }

        public bool IsIndeterminate
        {
            get => (bool)GetValue(IsIndeterminateProperty);
            set => SetValue(IsIndeterminateProperty, value);
        }

        public double Value
        {
            get => (double)GetValue(ValueProperty);
            set => SetValue(ValueProperty, value);
        }

        public double Maximum
        {
            get => (double)GetValue(MaximumProperty);
            set => SetValue(MaximumProperty, value);
        }

        private static void OnVisualStateChanged(DependencyObject sender, DependencyPropertyChangedEventArgs args)
        {
            (sender as ProgressStrip)?.UpdateIndicator();
        }

        private void UpdateIndicator()
        {
            if (Indicator == null || Shift == null)
            {
                return;
            }

            var width = ActualWidth;
            if (width <= 0)
            {
                return;
            }

            if (IsIndeterminate)
            {
                StartIndeterminate(width);
                return;
            }

            StopIndeterminate();
            var maximum = Maximum > 0 ? Maximum : 1;
            var fraction = Math.Max(0, Math.Min(1, Value / maximum));
            Indicator.Width = Math.Max(0, width * fraction);
            Shift.X = 0;
        }

        private void StartIndeterminate(double width)
        {
            var segment = Math.Max(72, width * 0.28);
            Indicator.Width = segment;

            if (_storyboard != null)
            {
                return;
            }

            var animation = new DoubleAnimation
            {
                From = -segment,
                To = width,
                Duration = new Duration(TimeSpan.FromSeconds(1.4)),
                RepeatBehavior = RepeatBehavior.Forever
            };

            _storyboard = new Storyboard();
            _storyboard.Children.Add(animation);
            Storyboard.SetTarget(animation, Shift);
            Storyboard.SetTargetProperty(animation, new PropertyPath("X"));
            _storyboard.Begin(this, true);
        }

        private void StopIndeterminate()
        {
            if (_storyboard == null)
            {
                return;
            }

            _storyboard.Stop(this);
            _storyboard = null;
        }
    }
}
