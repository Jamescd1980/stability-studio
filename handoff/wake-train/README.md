# Wake words: Hey Myra / Hey Nari / Hey Orla

Pi only wakes, listens (STT), and speaks (TTS). Create thinking = **Nari**. Display/polish = **Orla**.

## Train (ComfyBox)

```bash
ssh comfybox
cd /mnt/game/openwakeword-train
bash ./train_hey_nari_orla.sh   # or already running via nohup
# logs: logs/train_hey_nari.log, logs/train_hey_orla.log, logs/train_nari_orla_wrapper.log
```

When both ONNX files exist under `trained_wake_words/`:

```bash
bash ./install_nari_orla_on_myra.sh
ssh myra 'bash ~/studio-edge/restart_edge.sh'
```

`hey_jan.onnx` is retired (`hey_jan.onnx.retired` on the Pi).

## Check progress

```bash
ssh comfybox 'tail -20 /mnt/game/openwakeword-train/logs/train_nari_orla_wrapper.log'
ssh comfybox 'ls -la /mnt/game/openwakeword-train/trained_wake_words/hey_*.onnx'
```
