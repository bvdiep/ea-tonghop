# Spawn the conversion input on Modal (server-side, survives local disconnect).
import modal

app = modal.App("ssog-spawn")


@app.local_entrypoint()
def main(ply: str, out: str):
    f = modal.Function.from_name("ssog-convert-real", "convert")
    handle = f.spawn(ply, out)
    print("SPAWNED:", handle.object_id if hasattr(handle, "object_id") else handle)
