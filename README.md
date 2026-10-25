# CortaLive — protótipo com servidor

Esta pasta adiciona uma API de servidor que tenta obter vídeos públicos do YouTube e criar arquivos MP4 usando yt-dlp + FFmpeg. **Não há análise real por IA ainda**: os trechos são distribuídos ao longo do vídeo. Não processa lives privadas, conteúdo que exige login ou vídeos bloqueados pelo YouTube.

## Importante antes de usar
- O servidor ainda precisa ser hospedado e ter um endereço HTTPS público. O HTML atual ainda não está conectado automaticamente a uma API hospedada.
- Use apenas vídeos que você criou ou para os quais tem autorização para baixar e editar. Respeite direitos autorais e os termos da plataforma.
- Um servidor gratuito pode dormir, limitar processamento/armazenamento ou não permitir tarefas longas. Lives longas podem exceder os limites.
- Esta API não inclui autenticação, limites de uso robustos nem fila de tarefas; não a publique sem adicionar proteção contra abuso.

## Rodar para testes no computador
Requer Python 3.11+ e FFmpeg instalado.

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```
Teste `http://localhost:8000/health`. Documentação interativa: `http://localhost:8000/docs`.

## Implantação
O `backend/Dockerfile` instala FFmpeg e executa a API. Publique o diretório `backend` em um serviço que aceite Docker, configure uma URL pública HTTPS e teste `/health`. Só então o frontend poderá ser ligado a essa URL. A disponibilidade de planos gratuitos muda conforme o provedor.

## Estado real do projeto
- Servidor: código inicial incluído, não hospedado nem testado em um ambiente de produção.
- Cortes: FFmpeg gera MP4 a partir de pontos espaçados no vídeo.
- IA para achar momentos virais: ainda não implementada.
- Integração frontend ↔ servidor: ainda precisa ser ligada após a hospedagem.
