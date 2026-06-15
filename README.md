# Prism Kenz

Prism Kenz é um protótipo de câmera virtual/filtro ao vivo feito em Python, inspirado em ferramentas como Prism Lens.
O projeto captura a imagem da webcam, aplica efeitos em tempo real e permite testes com troca de fundo, blur, suavização e segmentação por IA.

> Status: protótipo funcional em desenvolvimento.

## Recursos atuais

* Captura de webcam com OpenCV
* Preview em tempo real
* Interface simples com sliders via OpenCV
* Espelhamento da câmera
* Correção de cor básica
* Filtro beauty simples
* Blur de fundo
* Troca de fundo por imagem
* Segmentação com RVM / Robust Video Matting
* Suporte a CUDA via PyTorch
* Profiler de performance por etapa
* Otimizações para rodar perto de 30 FPS em 720p
* Estrutura inicial para câmera virtual com `pyvirtualcam`

## Stack

* Python 3.12
* OpenCV
* NumPy
* PyTorch
* Robust Video Matting
* pyvirtualcam
* CUDA, quando disponível

## Estrutura do projeto

```text
prism_kenz/
├── main.py
├── config.py
├── performance.py
├── requirements.txt
├── benchmark_compose.py
├── camera/
├── effects/
├── ui/
├── assets/
└── prism_kenz_csharp/
```

A pasta `prism_kenz_csharp/` é uma versão experimental em C#/.NET criada para estudar uma futura versão mais robusta para Windows.

## Requisitos

* Windows
* Python 3.12 64-bit
* Webcam
* GPU NVIDIA recomendada para RVM com CUDA
* Driver NVIDIA atualizado
* Opcional: OBS Virtual Camera ou outra câmera virtual compatível

## Instalação

Clone o repositório:

```powershell
git clone https://github.com/kemizin/prism_kenz.git
cd prism_kenz
```

Crie o ambiente virtual:

```powershell
py -3.12 -m venv .venv
```

Ative o ambiente:

```powershell
.\.venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear a ativação:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Instale as dependências:

```powershell
pip install -r requirements.txt
```

## Teste de CUDA

Use este comando para verificar se o PyTorch está enxergando a GPU:

```powershell
python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'sem cuda')"
```

Resultado esperado em máquina com NVIDIA/CUDA funcionando:

```text
True
NVIDIA GeForce ...
```

## Como rodar

```powershell
python main.py
```

O app deve abrir a câmera e mostrar o preview com os efeitos ativos.

## Configuração

As principais opções ficam em `config.py`.

Exemplo de configuração recomendada para teste:

```python
WIDTH = 1280
HEIGHT = 720
FPS = 30

BACKGROUND_MODE = "image"

RVM_DEVICE = "cuda"
RVM_MODEL = "mobilenetv3"
RVM_INFERENCE_WIDTH = 640
RVM_INFERENCE_HEIGHT = 360
RVM_DOWNSAMPLE_RATIO = 0.20
RVM_PROCESS_EVERY_N_FRAMES = 2
USE_FP16 = True

BEAUTY_MODE = "off"

MASK_BLUR_KERNEL = 1
MASK_FEATHER_KERNEL = 3
```

## Fundos personalizados

Coloque imagens de fundo em:

```text
assets/backgrounds/
```

Por padrão, o projeto procura:

```text
assets/backgrounds/bg.jpg
```

## Performance

O projeto possui logs de performance para medir etapas como:

* captura
* correção de cor
* beauty
* segmentação
* resize de alpha
* preparação do fundo
* composição
* preview
* envio para câmera virtual
* tempo total do pipeline

Exemplo:

```text
[Performance] FPS: 30.0 | capture: 0.7 ms | segmentation: 10.4 ms | compose: 8.0 ms | total: 33.3 ms
```

## Observações

Este projeto começou como um protótipo rápido em Python para validar a ideia.
Python foi escolhido pela velocidade de desenvolvimento e facilidade de testar IA, OpenCV e modelos de segmentação.

Uma versão futura mais robusta pode usar:

* C#/.NET para app Windows
* OpenCvSharp para câmera
* ONNX Runtime para inferência
* DirectML, CUDA ou TensorRT para aceleração
* UI mais completa
* integração melhor com câmera virtual

## Roadmap

* [ ] Melhorar câmera virtual
* [ ] Adicionar presets
* [ ] Adicionar hotkeys
* [ ] Criar galeria de fundos
* [ ] Salvar configurações em JSON
* [ ] Melhorar interface
* [ ] Testar ONNX Runtime
* [ ] Evoluir versão C#/.NET
* [ ] Criar instalador `.exe`

## Licença

Projeto pessoal/experimental.
Antes de distribuir publicamente, revisar licenças das bibliotecas e modelos usados, especialmente modelos de IA externos.
