using System;
using System.Windows;

namespace UninstallerTool.Infrastructure
{
    internal static class WindowSizing
    {
        public static void Fit(Window window)
        {
            if (window == null)
            {
                return;
            }

            var area = SystemParameters.WorkArea;
            var availableWidth = Math.Max(320, area.Width - 16);
            var availableHeight = Math.Max(240, area.Height - 16);

            if (window.MinWidth > availableWidth)
            {
                window.MinWidth = availableWidth;
            }

            if (window.MinHeight > availableHeight)
            {
                window.MinHeight = availableHeight;
            }

            if (!double.IsNaN(window.Width) && window.Width > availableWidth)
            {
                window.Width = availableWidth;
            }

            if (!double.IsNaN(window.Height) && window.Height > availableHeight)
            {
                window.Height = availableHeight;
            }

            if (!double.IsInfinity(window.MaxWidth) && window.MaxWidth < window.MinWidth)
            {
                window.MaxWidth = window.MinWidth;
            }

            if (!double.IsInfinity(window.MaxHeight) && window.MaxHeight < window.MinHeight)
            {
                window.MaxHeight = window.MinHeight;
            }

            if (!double.IsNaN(window.Width) && window.Width < window.MinWidth)
            {
                window.Width = window.MinWidth;
            }

            if (!double.IsNaN(window.Height) && window.Height < window.MinHeight)
            {
                window.Height = window.MinHeight;
            }
        }
    }
}
