using System;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;
using Microsoft.Win32;
using UninstallerTool.Infrastructure;

namespace UninstallerTool.Theme
{
    internal sealed class Palette
    {
        public Palette(
            string background,
            string surface,
            string surfaceAlt,
            string text,
            string textSecondary,
            string textTertiary,
            string border,
            string borderHover,
            string primary,
            string primaryHover,
            string primaryPressed,
            string primarySoft,
            string success,
            string successBg,
            string error,
            string errorBg,
            string progressBg,
            string scrollHandle)
        {
            Background = Parse(background);
            Surface = Parse(surface);
            SurfaceAlt = Parse(surfaceAlt);
            Text = Parse(text);
            TextSecondary = Parse(textSecondary);
            TextTertiary = Parse(textTertiary);
            Border = Parse(border);
            BorderHover = Parse(borderHover);
            Primary = Parse(primary);
            PrimaryHover = Parse(primaryHover);
            PrimaryPressed = Parse(primaryPressed);
            PrimarySoft = Parse(primarySoft);
            Success = Parse(success);
            SuccessBg = Parse(successBg);
            Error = Parse(error);
            ErrorBg = Parse(errorBg);
            ProgressBg = Parse(progressBg);
            ScrollHandle = Parse(scrollHandle);
        }

        public Color Background { get; }
        public Color Surface { get; }
        public Color SurfaceAlt { get; }
        public Color Text { get; }
        public Color TextSecondary { get; }
        public Color TextTertiary { get; }
        public Color Border { get; }
        public Color BorderHover { get; }
        public Color Primary { get; }
        public Color PrimaryHover { get; }
        public Color PrimaryPressed { get; }
        public Color PrimarySoft { get; }
        public Color Success { get; }
        public Color SuccessBg { get; }
        public Color Error { get; }
        public Color ErrorBg { get; }
        public Color ProgressBg { get; }
        public Color ScrollHandle { get; }

        public static Palette Light { get; } = new Palette(
            "#F6F6F8", "#FFFFFF", "#FAFAFC", "#191922", "#71717D", "#9C9CA6",
            "#E7E7EE", "#C9C9F0", "#4F46E5", "#4338CA", "#3730A3", "#EEEEFC",
            "#15803D", "#E9F7EE", "#DC2626", "#FDEEEE", "#EBEBF1", "#CDCDD6");

        public static Palette Dark { get; } = new Palette(
            "#16161B", "#232329", "#2A2A32", "#F0F0F4", "#A5A5B0", "#6E6E7A",
            "#31313A", "#5252A8", "#6366F1", "#5558E8", "#4346C5", "#2C2C4A",
            "#4ADE80", "#1D3328", "#F87171", "#3A2326", "#2C2C34", "#4A4A55");

        private static Color Parse(string hex)
        {
            return (Color)ColorConverter.ConvertFromString(hex);
        }
    }

    internal static class ThemeManager
    {
        public const string BackgroundBrushKey = "AppBackgroundBrush";
        public const string SurfaceBrushKey = "SurfaceBrush";
        public const string SurfaceAltBrushKey = "SurfaceAltBrush";
        public const string TextBrushKey = "TextBrush";
        public const string TextSecondaryBrushKey = "TextSecondaryBrush";
        public const string TextTertiaryBrushKey = "TextTertiaryBrush";
        public const string BorderBrushKey = "BorderBrush";
        public const string BorderHoverBrushKey = "BorderHoverBrush";
        public const string PrimaryBrushKey = "PrimaryBrush";
        public const string PrimaryHoverBrushKey = "PrimaryHoverBrush";
        public const string PrimaryPressedBrushKey = "PrimaryPressedBrush";
        public const string PrimarySoftBrushKey = "PrimarySoftBrush";
        public const string SuccessBrushKey = "SuccessBrush";
        public const string SuccessBgBrushKey = "SuccessBgBrush";
        public const string ErrorBrushKey = "ErrorBrush";
        public const string ErrorBgBrushKey = "ErrorBgBrush";
        public const string ProgressBgBrushKey = "ProgressBgBrush";
        public const string ScrollHandleBrushKey = "ScrollHandleBrush";

        private static bool _initialized;

        public static Palette CurrentPalette { get; private set; } = Palette.Light;

        public static bool IsDark { get; private set; }

        public static event EventHandler ThemeChanged;

        public static void Initialize()
        {
            if (_initialized)
            {
                return;
            }

            _initialized = true;
            Apply(DetectPalette());
            SystemEvents.UserPreferenceChanged += OnUserPreferenceChanged;
        }

        public static bool Refresh()
        {
            var palette = DetectPalette();
            if (palette == CurrentPalette)
            {
                return false;
            }

            Apply(palette);
            return true;
        }

        public static void AttachWindow(Window window)
        {
            if (window == null)
            {
                return;
            }

            ApplyWindowTheme(window);

            EventHandler handler = (sender, args) => ApplyWindowTheme(window);
            ThemeChanged += handler;
            window.Closed += (sender, args) => ThemeChanged -= handler;
        }

        private static void ApplyWindowTheme(Window window)
        {
            var handle = new WindowInteropHelper(window).Handle;
            NativeMethods.SetDarkTitleBar(handle, IsDark);
        }

        public static void Apply(Palette palette)
        {
            CurrentPalette = palette;
            IsDark = palette == Palette.Dark;

            var resources = Application.Current.Resources;
            resources[BackgroundBrushKey] = Brush(palette.Background);
            resources[SurfaceBrushKey] = Brush(palette.Surface);
            resources[SurfaceAltBrushKey] = Brush(palette.SurfaceAlt);
            resources[TextBrushKey] = Brush(palette.Text);
            resources[TextSecondaryBrushKey] = Brush(palette.TextSecondary);
            resources[TextTertiaryBrushKey] = Brush(palette.TextTertiary);
            resources[BorderBrushKey] = Brush(palette.Border);
            resources[BorderHoverBrushKey] = Brush(palette.BorderHover);
            resources[PrimaryBrushKey] = Brush(palette.Primary);
            resources[PrimaryHoverBrushKey] = Brush(palette.PrimaryHover);
            resources[PrimaryPressedBrushKey] = Brush(palette.PrimaryPressed);
            resources[PrimarySoftBrushKey] = Brush(palette.PrimarySoft);
            resources[SuccessBrushKey] = Brush(palette.Success);
            resources[SuccessBgBrushKey] = Brush(palette.SuccessBg);
            resources[ErrorBrushKey] = Brush(palette.Error);
            resources[ErrorBgBrushKey] = Brush(palette.ErrorBg);
            resources[ProgressBgBrushKey] = Brush(palette.ProgressBg);
            resources[ScrollHandleBrushKey] = Brush(palette.ScrollHandle);

            ThemeChanged?.Invoke(null, EventArgs.Empty);
        }

        public static Palette DetectPalette()
        {
            if (SystemParameters.HighContrast)
            {
                return Palette.Light;
            }

            try
            {
                using (var key = Registry.CurrentUser.OpenSubKey(
                           @"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"))
                {
                    if (key?.GetValue("AppsUseLightTheme") is int value)
                    {
                        return value == 0 ? Palette.Dark : Palette.Light;
                    }
                }
            }
            catch (Exception)
            {
                return Palette.Light;
            }

            return Palette.Light;
        }

        private static SolidColorBrush Brush(Color color)
        {
            var brush = new SolidColorBrush(color);
            brush.Freeze();
            return brush;
        }

        private static void OnUserPreferenceChanged(object sender, UserPreferenceChangedEventArgs e)
        {
            if (e.Category == UserPreferenceCategory.General)
            {
                Refresh();
            }
        }
    }
}
