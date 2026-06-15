# Prism Kenz C#

Esta pasta contem a futura base robusta do Prism Kenz para Windows em C#/.NET.
O projeto Python na pasta pai continua sendo o laboratorio/prototipo para testar
efeitos, segmentacao e ideias rapidamente. Nenhum arquivo Python e necessario
para compilar ou executar esta versao C#.

## Estado atual

- Captura de webcam com OpenCvSharp.
- Preview ao vivo em uma janela OpenCV.
- Espelhamento configuravel.
- Correcao de cor basica.
- Beauty simples opcional.
- Pipeline modular e profiler por etapa.
- `ISegmenter`, `DummySegmenter` e stub de `OnnxSegmenter`.
- Background blur/image preparado para uma futura mascara de segmentacao.
- Stub isolado para camera virtual.

O MVP usa `DummySegmenter(returnFullMask: false)`, portanto background replacement
fica inativo ate uma implementacao real de segmentacao ser conectada.

## Requisitos

- Windows
- .NET SDK 10
- Webcam

## Executar

```powershell
cd prism_kenz_csharp
dotnet restore
dotnet run --project src/PrismKenz.App/PrismKenz.App.csproj
```

Pressione `Q`, `ESC` ou `Ctrl+C` para sair.

As configuracoes ficam em `src/PrismKenz.App/appsettings.json`.

Configuracoes de captura:

- `CameraBackend`: `DSHOW` ou `MSMF`.
- `CameraFourCC`: normalmente `MJPG`.
- `UseThreadedCapture`: publica apenas o frame mais recente sem bloquear o pipeline.
- `CameraBufferSize`: tamanho solicitado ao backend, normalmente `1`.

## Arquitetura

- `Camera/CameraCapture.cs`: somente captura frames.
- `Pipeline/VideoPipeline.cs`: coordena o processamento.
- `Effects/`: efeitos independentes.
- `Effects/Segmentation/ISegmenter.cs`: contrato para motores de recorte.
- `Pipeline/PerformanceProfiler.cs`: tempos de capture_wait_read,
  get_latest_frame, color, beauty, segmentation, background, compose, preview
  e total.
- `Camera/VirtualCameraOutput.cs`: ponto futuro para saida virtual.

## Proximos passos

- Integrar ONNX Runtime.
- Portar RVM, MODNet ou outro modelo de segmentacao.
- Implementar camera virtual real no Windows.
- Criar uma UI melhor.
- Salvar e carregar presets.
