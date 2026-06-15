using System.Diagnostics;
using OpenCvSharp;
using PrismKenz.App.Camera;
using PrismKenz.App.Effects;
using PrismKenz.App.Effects.Segmentation;
using PrismKenz.App.Pipeline;
using PrismKenz.App.UI;

namespace PrismKenz.App;

internal static class Program
{
    private static bool _stopRequested;

    public static int Main()
    {
        Console.CancelKeyPress += (_, eventArgs) =>
        {
            eventArgs.Cancel = true;
            _stopRequested = true;
        };

        try
        {
            var config = AppConfig.Load();

            using var camera = new CameraCapture(config);
            using ISegmenter segmenter = new DummySegmenter(returnFullMask: false);
            using var pipeline = new VideoPipeline(
                config,
                new ColorCorrectionEffect(),
                new BeautyEffect(config),
                new BackgroundEffect(config),
                segmenter);
            using var preview = new PreviewWindow();
            using var virtualCamera = new VirtualCameraOutput();
            var profiler = new PerformanceProfiler(
                config.FpsLogIntervalSeconds,
                config.ShowPerformanceLogs);

            Console.WriteLine("[PrismKenz] C# MVP iniciado. Pressione Q, ESC ou Ctrl+C para sair.");

            while (!_stopRequested)
            {
                var timings = profiler.BeginFrame();
                var totalStartedAt = Stopwatch.GetTimestamp();
                Mat frame = null!;

                var captured = timings.Measure(
                    PerformanceStages.GetLatestFrame,
                    () => camera.TryRead(out frame));
                timings.SetValue(
                    PerformanceStages.CaptureWaitRead,
                    camera.CaptureWaitReadMilliseconds);

                if (!captured)
                {
                    Console.WriteLine("[Camera] Nao foi possivel capturar um frame.");
                    break;
                }

                using (frame)
                using (var output = pipeline.Process(frame, timings))
                {
                    var snapshot = profiler.Snapshot();
                    var shouldClose = timings.Measure(
                        PerformanceStages.Preview,
                        () => preview.Show(output, snapshot.Fps));

                    virtualCamera.Send(output);
                    timings.SetElapsed(PerformanceStages.Total, totalStartedAt);
                    profiler.RecordFrame(timings);
                    profiler.MaybeLog();

                    if (shouldClose)
                    {
                        break;
                    }
                }
            }

            return 0;
        }
        catch (Exception exception)
        {
            Console.Error.WriteLine($"[PrismKenz] Erro fatal: {exception.Message}");
            Console.Error.WriteLine(exception);
            return 1;
        }
    }
}
