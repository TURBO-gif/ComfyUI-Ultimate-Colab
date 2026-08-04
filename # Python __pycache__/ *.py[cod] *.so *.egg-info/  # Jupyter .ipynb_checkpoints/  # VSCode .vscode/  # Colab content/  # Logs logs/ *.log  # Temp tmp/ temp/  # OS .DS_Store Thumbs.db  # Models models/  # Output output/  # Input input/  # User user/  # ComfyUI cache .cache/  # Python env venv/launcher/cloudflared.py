from .utils import run


def install():

    run(
        "wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared"
    )

    run("chmod +x cloudflared")
