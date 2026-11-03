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
            Action<IReadOnlyList<ProgramEntry>> registryLoaded,
            Action<IReadOnlyList<ProgramEntry>> storeLoaded,
            CancellationToken token,
            bool forceStore = false)
        {
            var registry = await Task.Run(() => RegistryScanner.ScanInstalledPrograms(), token);
            if (token.IsCancellationRequested)
            {
                return;
            }

            registryLoaded?.Invoke(registry);

            if (!forceStore)
            {
                var (cached, fresh) = StoreApps.LoadCache();
                if (cached.Count > 0)
                {
                    storeLoaded?.Invoke(cached);
                }

                if (fresh || token.IsCancellationRequested)
                {
                    return;
                }

                await Task.Delay(StoreScanDelayMilliseconds, token);
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
