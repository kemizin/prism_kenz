using OpenCvSharp;
using PrismKenz.App.Effects;
using PrismKenz.App.Effects.Segmentation;
using PrismKenz.App.Utils;

namespace PrismKenz.App.Pipeline;

public sealed class VideoPipeline : IDisposable
{
    private readonly AppConfig _config;
    private readonly ColorCorrectionEffect _colorCorrection;
    private readonly BeautyEffect _beauty;
    private readonly BackgroundEffect _background;
    private readonly ISegmenter _segmenter;

    public VideoPipeline(
        AppConfig config,
        ColorCorrectionEffect colorCorrection,
        BeautyEffect beauty,
        BackgroundEffect background,
        ISegmenter segmenter)
    {
        _config = config;
        _colorCorrection = colorCorrection;
        _beauty = beauty;
        _background = background;
        _segmenter = segmenter;
    }

    public Mat Process(Mat input, FrameTimings timings)
    {
        var working = FrameUtils.CloneOrMirror(input, _config.MirrorCamera);

        timings.Measure(PerformanceStages.Color, () => _colorCorrection.Apply(working));
        timings.Measure(PerformanceStages.Beauty, () => _beauty.Apply(working));

        if (!_background.IsActive)
        {
            return working;
        }

        using var alpha = timings.Measure(
            PerformanceStages.Segmentation,
            () => _segmenter.Segment(working));

        if (alpha is null)
        {
            return working;
        }

        using var preparedBackground = timings.Measure(
            PerformanceStages.Background,
            () => _background.Prepare(working));

        if (preparedBackground is null)
        {
            return working;
        }

        var output = timings.Measure(
            PerformanceStages.Compose,
            () => _background.Compose(working, preparedBackground, alpha));
        working.Dispose();
        return output;
    }

    public void Dispose()
    {
        _background.Dispose();
    }
}
