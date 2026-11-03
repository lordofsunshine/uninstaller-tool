using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using UninstallerTool.Infrastructure;
using UninstallerTool.Models;

namespace UninstallerTool.Core
{
    internal static class ProgramLoader
    {
        private const int StoreScanDelayMilliseconds = 1500;

        public static async Task LoadAsync(
            Action<IList<ProgramEntry>> registryLoaded,
            Action<IList<ProgramEntry>> storeLoaded,
            CancellationToken token,
            bool forceStore = false)
        {
            var registry = await Task.Factory.StartNew(() => RegistryScanner.ScanInstalledPrograms(), token);
            if (token.IsCancellationRequested)
            {
                return;
            }

            registryLoaded?.Invoke(registry);

            if (!forceStore)
            {
                var cache = StoreApps.LoadCache();
                if (cache.Programs.Count > 0)
                {
                    storeLoaded?.Invoke(cache.Programs);
                }

                if (cache.Fresh || token.IsCancellationRequested)
                {
                    return;
                }

                await TaskEx.Delay(StoreScanDelayMilliseconds, token);
            }

            List<ProgramEntry> programs;
            try
            {
                programs = await StoreApps.FetchAsync();
            }
            catch (TimeoutException exception)
            {
                Log.Warn("Store apps are unavailable: " + exception.Message);
                return;
            }
            catch (IOException exception)
            {
                Log.Warn("Store apps are unavailable: " + exception.Message);
                return;
            }
            catch (InvalidOperationException exception)
            {
                Log.Warn("Store apps are unavailable: " + exception.Message);
                return;
            }

            if (token.IsCancellationRequested)
            {
                return;
            }

            StoreApps.SaveCache(programs);
            storeLoaded?.Invoke(programs);
        }
    }
}
