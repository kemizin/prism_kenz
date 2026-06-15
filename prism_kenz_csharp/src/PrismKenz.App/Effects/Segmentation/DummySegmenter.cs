using OpenCvSharp;

namespace PrismKenz.App.Effects.Segmentation;

public sealed class DummySegmenter : ISegmenter
{
    private readonly bool _returnFullMask;

    public DummySegmenter(bool returnFullMask)
    {
        _returnFullMask = returnFullMask;
    }

    public Mat? Segment(Mat frame)
    {
        if (!_returnFullMask)
        {
            return null;
        }

        return new Mat(
            frame.Rows,
            frame.Cols,
            MatType.CV_32FC1,
            Scalar.All(1.0));
    }

    public void Dispose()
    {
    }
}
