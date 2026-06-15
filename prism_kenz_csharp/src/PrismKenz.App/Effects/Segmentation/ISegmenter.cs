using OpenCvSharp;

namespace PrismKenz.App.Effects.Segmentation;

public interface ISegmenter : IDisposable
{
    Mat? Segment(Mat frame);
}
