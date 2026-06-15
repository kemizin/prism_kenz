using System.Diagnostics;

namespace PrismKenz.App.Pipeline;

public static class PerformanceStages
{
    public const string CaptureWaitRead = "capture_wait_read";
    public const string GetLatestFrame = "get_latest_frame";
    public const string Color = "color";
    public const string Beauty = "beauty";
    public const string Segmentation = "segmentation";
    public const string Background = "background";
    public const string Compose = "compose";
    public const string Preview = "preview";
    public const string Total = "total";

    public static readonly string[] All =
    [
        CaptureWaitRead,
        GetLatestFrame,
        Color,
        Beauty,
        Segmentation,
        Background,
        Compose,
        Preview,
        Total,
    ];
}

public sealed class FrameTimings
{
    private readonly Dictionary<string, double> _values = [];

    public IReadOnlyDictionary<string, double> Values => _values;

    public void Measure(string stage, Action action)
    {
        var startedAt = Stopwatch.GetTimestamp();
        action();
        SetElapsed(stage, startedAt);
    }

    public T Measure<T>(string stage, Func<T> action)
    {
        var startedAt = Stopwatch.GetTimestamp();
        var result = action();
        SetElapsed(stage, startedAt);
        return result;
    }

    public void SetElapsed(string stage, long startedAt)
    {
        _values[stage] = Stopwatch.GetElapsedTime(startedAt).TotalMilliseconds;
    }

    public void SetValue(string stage, double value)
    {
        _values[stage] = Math.Max(0, value);
    }
}

public sealed record PerformanceSnapshot(
    double Fps,
    IReadOnlyDictionary<string, double> Timings);

public sealed class PerformanceProfiler
{
    private readonly double _logIntervalSeconds;
    private readonly bool _showLogs;
    private readonly Dictionary<string, double> _sums = [];
    private readonly Dictionary<string, double> _ema = [];
    private long _lastLogAt = Stopwatch.GetTimestamp();
    private int _frameCount;
    private bool _hasEma;

    public PerformanceProfiler(double logIntervalSeconds, bool showLogs)
    {
        _logIntervalSeconds = Math.Max(0.1, logIntervalSeconds);
        _showLogs = showLogs;

        foreach (var stage in PerformanceStages.All)
        {
            _sums[stage] = 0;
            _ema[stage] = 0;
        }
    }

    public FrameTimings BeginFrame() => new();

    public void RecordFrame(FrameTimings timings)
    {
        foreach (var stage in PerformanceStages.All)
        {
            var value = timings.Values.GetValueOrDefault(stage, 0);
            _sums[stage] += value;
            _ema[stage] = _hasEma ? (_ema[stage] * 0.90) + (value * 0.10) : value;
        }

        _hasEma = true;
        _frameCount++;
    }

    public PerformanceSnapshot Snapshot()
    {
        var total = _ema[PerformanceStages.Total];
        var fps = total > 0 ? 1000.0 / total : 0;
        return new PerformanceSnapshot(fps, new Dictionary<string, double>(_ema));
    }

    public void MaybeLog()
    {
        if (Stopwatch.GetElapsedTime(_lastLogAt).TotalSeconds < _logIntervalSeconds)
        {
            return;
        }

        if (_showLogs && _frameCount > 0)
        {
            var averages = PerformanceStages.All.ToDictionary(
                stage => stage,
                stage => _sums[stage] / _frameCount);
            var total = averages[PerformanceStages.Total];
            var fps = total > 0 ? 1000.0 / total : 0;
            var stageText = string.Join(
                " | ",
                PerformanceStages.All.Select(stage => $"{stage}: {averages[stage]:0.0} ms"));

            Console.WriteLine($"[Performance] FPS: {fps:0.0} | {stageText}");
        }

        foreach (var stage in PerformanceStages.All)
        {
            _sums[stage] = 0;
        }

        _frameCount = 0;
        _lastLogAt = Stopwatch.GetTimestamp();
    }
}
