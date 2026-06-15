using OpenCvSharp;

namespace PrismKenz.App.Camera;

public sealed class VirtualCameraOutput : IDisposable
{
    public void Send(Mat frame)
    {
        // Future integration point for a Windows virtual camera implementation.
    }

    public void Dispose()
    {
    }
}
