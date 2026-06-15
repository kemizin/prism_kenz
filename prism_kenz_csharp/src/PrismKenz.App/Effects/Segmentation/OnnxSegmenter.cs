using OpenCvSharp;

namespace PrismKenz.App.Effects.Segmentation;

public sealed class OnnxSegmenter : ISegmenter
{
    private readonly string _modelPath;

    public OnnxSegmenter(string modelPath)
    {
        _modelPath = modelPath;
    }

    public Mat? Segment(Mat frame)
    {
        // Future implementation:
        // 1. Resize/normalize the BGR frame into the model tensor.
        // 2. Run Microsoft.ML.OnnxRuntime.InferenceSession.
        // 3. Convert the output tensor into a CV_32FC1 alpha matte.
        throw new NotImplementedException(
            $"ONNX segmentation is not implemented yet. Model: {_modelPath}");
    }

    public void Dispose()
    {
        // Dispose the future InferenceSession here.
    }
}
