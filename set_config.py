import os
import sys
import configparser
import argparse


config = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
parser = argparse.ArgumentParser(description="Setup a config file with the default IO directory structure.")

parser.add_argument("--base_io_directory", type=str, default="./")
parser.add_argument("--base_directory", type=str, default="./")
parser.add_argument("--root_models_prefix", type=str, default="input/models/")
parser.add_argument("--root_outputs_prefix", type=str, default="output/models/")
parser.add_argument("--model_name", type=str, default="v1-5-pruned-emaonly")
parser.add_argument("--clip_model_name", type=str, default="vit-large-patch14")
args = parser.parse_args()

BASE_IO_DIRECTORY = args.base_io_directory
BASE_DIRECTORY = args.base_directory
ROOT_MODELS_PREFIX = args.root_models_prefix
ROOT_OUTPUTS_PREFIX = args.root_outputs_prefix
MODEL_NAME = args.model_name
CLIP_MODEL_NAME = args.clip_model_name
CHECKPOINT = f"{MODEL_NAME}.safetensors"
# Please note that using RawConfigParser's set functions, you can assign
# non-string values to keys internally, but will receive an error when
# attempting to write to a file or when you get it in non-raw mode. Setting
# values using the mapping protocol or ConfigParser's set() does not allow
# such assignments to take place.
config["BASE"] = {
                    "BASE_IO_DIRECTORY": f"{BASE_IO_DIRECTORY}",
                    "BASE_DIRECTORY": f"{BASE_DIRECTORY}",
                    "ROOT_MODELS_PREFIX": f"{ROOT_MODELS_PREFIX}",
                    "ROOT_OUTPUTS_PREFIX": f"{ROOT_OUTPUTS_PREFIX}",
                    "MODEL_NAME": f"{MODEL_NAME}",
                    "CLIP_MODEL_NAME": f"{CLIP_MODEL_NAME}",
                    "CHECKPOINT": CHECKPOINT
                    }

ROOT_MODELS_DIR = (os.path.join(BASE_IO_DIRECTORY, ROOT_MODELS_PREFIX))
ROOT_OUTPUTS_DIR = (os.path.join(BASE_IO_DIRECTORY, ROOT_OUTPUTS_PREFIX))
SD_DEFAULT_MODEL_DIR = os.path.join(ROOT_MODELS_DIR, MODEL_NAME)
CLIP_MODELS_DIR = os.path.join(ROOT_MODELS_DIR, "clip")
TEXT_EMBEDDER_DIR = (
    os.path.join(CLIP_MODELS_DIR, "text_embedder/")
)
config["DIRS"] = dict(
        ROOT_MODELS_DIR = ROOT_MODELS_DIR,
        ROOT_OUTPUTS_DIR = ROOT_OUTPUTS_DIR,
        SD_DEFAULT_MODEL_DIR = SD_DEFAULT_MODEL_DIR,
        CLIP_MODELS_DIR = CLIP_MODELS_DIR,
        TEXT_EMBEDDER_DIR = TEXT_EMBEDDER_DIR
        )

config["PATHS"] = dict(
    CHECKPOINT_PATH = (
    os.path.join(ROOT_MODELS_DIR, CHECKPOINT)
    ),
    TEXT_EMBEDDER_PATH = (
        os.path.join(TEXT_EMBEDDER_DIR, "text_embedder.safetensors")
    ),
    TOKENIZER_PATH = (
        os.path.join(TEXT_EMBEDDER_DIR, "tokenizer/")
    ),
    TEXT_MODEL_PATH = (
        os.path.join(TEXT_EMBEDDER_DIR, CLIP_MODEL_NAME)
    ),

    IMAGE_PROCESSOR_PATH = (
        os.path.join(CLIP_MODELS_DIR, "clip_image_encoder/image_processor.ckpt")
    ),
    CLIP_MODEL_PATH = (
        os.path.join(CLIP_MODELS_DIR, "clip_image_encoder/clip_model.ckpt")
    ),
    IMAGE_ENCODER_PATH = (
        os.path.join(CLIP_MODELS_DIR, "clip_image_encoder/clip_image_encoder.ckpt")
    ),
    UNET_PATH = (
        os.path.join(SD_DEFAULT_MODEL_DIR, "unet.safetensors")
    ),
    AUTOENCODER_PATH = (
        os.path.join(SD_DEFAULT_MODEL_DIR, "autoencoder.safetensors")
    ),
    ENCODER_PATH = (
        os.path.join(SD_DEFAULT_MODEL_DIR, "encoder.safetensors")
    ),
    DECODER_PATH = (
        os.path.join(SD_DEFAULT_MODEL_DIR, "decoder.safetensors")
    ),
    LATENT_DIFFUSION_PATH = (
        os.path.join(SD_DEFAULT_MODEL_DIR, "latent_diffusion.safetensors")
    )
)

# Writing our configuration file to 'example.cfg'
with open('config.cfg', 'w') as configfile:
    config.write(configfile)