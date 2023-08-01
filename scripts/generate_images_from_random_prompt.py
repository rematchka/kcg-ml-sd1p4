"""
---
title: Generate images using stable diffusion with a prompt
summary: >
 Generate images using stable diffusion with a prompt
---

# Generate images using [stable diffusion](../index.html) with a prompt
"""

import time
import os
import sys
import torch
from datetime import datetime
import numpy as np

base_directory = "./"
sys.path.insert(0, base_directory)

from generation_task_result import GenerationTaskResult
from stable_diffusion.utils_backend import get_autocast, set_seed
from stable_diffusion.utils_image import save_images
from stable_diffusion_base_script import StableDiffusionBaseScript
from utility.labml import monit
from stable_diffusion.model.unet.unet_attention import CrossAttention
from cli_builder import CLI
import random
import json
import clip
from PIL import Image
import io
from chad_score.chad_score import get_chad_score

def get_image_features(image, device):
    model, preprocess = clip.load('ViT-L/14', device)

    image_input = preprocess(image).unsqueeze(0).to(device)

    # Encode the image
    with torch.no_grad():
        image_features = model.encode_image(image_input)

    image_features = image_features.to(torch.float32)
    return image_features

class Txt2Img(StableDiffusionBaseScript):
    """
    ### Text to image class
    """

    @torch.no_grad()
    def generate_images(self, *,
                        seed: int = 0,
                        batch_size: int = 1,
                        prompt: str,
                        h: int = 512, w: int = 512,
                        uncond_scale: float = 7.5,
                        low_vram: bool = False,
                        noise_fn=torch.randn,
                        temperature: float = 1.0,
                        ):
        """
        :param seed: the seed to use when generating the images
        :param dest_path: is the path to store the generated images
        :param batch_size: is the number of images to generate in a batch
        :param prompt: is the prompt to generate images with
        :param h: is the height of the image
        :param w: is the width of the image
        :param uncond_scale: is the unconditional guidance scale $s$. This is used for
            $\epsilon_\theta(x_t, c) = s\epsilon_\text{cond}(x_t, c) + (s - 1)\epsilon_\text{cond}(x_t, c_u)$
        :param low_vram: whether to limit VRAM usage
        """
        # Number of channels in the image
        c = 4
        # Image to latent space resolution reduction
        f = 8

        if seed == 0:
            seed = time.time_ns() % 2 ** 32

        set_seed(seed)
        # Adjust batch size based on VRAM availability
        if low_vram:
            batch_size = 1

        # Make a batch of prompts
        prompts = batch_size * [prompt]

        # AMP auto casting
        autocast = get_autocast()
        with autocast:
            un_cond, cond = self.get_text_conditioning(uncond_scale, prompts, batch_size)

            start_time = time.time()
            # [Sample in the latent space](../sampler/index.html).
            # `x` will be of shape `[batch_size, c, h / f, w / f]`
            x = self.sampler.sample(cond=cond,
                                    shape=[batch_size, c, h // f, w // f],
                                    uncond_scale=uncond_scale,
                                    uncond_cond=un_cond,
                                    noise_fn=noise_fn,
                                    temperature=temperature)

            # Capture the ending time
            end_time = time.time()

            # Calculate the execution time
            execution_time = end_time - start_time

            print("Sampling Time:", execution_time, "seconds")

            return self.decode_image(x)

    @torch.no_grad()
    def generate_images_from_embeddings(self, *,
                                        seed: int = 0,
                                        batch_size: int = 1,
                                        embedded_prompt: torch.Tensor,
                                        null_prompt: torch.Tensor,
                                        h: int = 512, w: int = 512,
                                        uncond_scale: float = 7.5,
                                        low_vram: bool = False,
                                        noise_fn=torch.randn,
                                        temperature: float = 1.0,
                                        ):
        """
        :param seed: the seed to use when generating the images
        :param dest_path: is the path to store the generated images
        :param batch_size: is the number of images to generate in a batch
        :param prompt: is the prompt to generate images with
        :param h: is the height of the image
        :param w: is the width of the image
        :param uncond_scale: is the unconditional guidance scale $s$. This is used for
            $\epsilon_\theta(x_t, c) = s\epsilon_\text{cond}(x_t, c) + (s - 1)\epsilon_\text{cond}(x_t, c_u)$
        :param low_vram: whether to limit VRAM usage
        """
        # Number of channels in the image
        c = 4
        # Image to latent space resolution reduction
        f = 8

        if seed == 0:
            seed = time.time_ns() % 2 ** 32

        set_seed(seed)
        # Adjust batch size based on VRAM availability
        if low_vram:
            batch_size = 1

        # Make a batch of prompts
        # prompts = batch_size * [embedded_prompt]
        # cond = torch.cat(prompts, dim=1)
        cond = embedded_prompt.unsqueeze(0)
        # print("cond shape: ", cond.shape)
        # print("uncond shape: ", null_prompt.shape)
        # prompt_list = ["a painting of a virus monster playing guitar", "a painting of a computer virus "]
        # AMP auto casting
        autocast = get_autocast()
        with autocast:

            # [Sample in the latent space](../sampler/index.html).
            # `x` will be of shape `[batch_size, c, h / f, w / f]`
            x = self.sampler.sample(cond=cond,
                                    shape=[batch_size, c, h // f, w // f],
                                    uncond_scale=uncond_scale,
                                    uncond_cond=null_prompt,
                                    noise_fn=noise_fn,
                                    temperature=temperature)

            return self.decode_image(x)


def main():
    opt = CLI('Generate images using stable diffusion with a prompt') \
        .prompts_file(check_exists=True, required=False) \
        .batch_size() \
        .output() \
        .sampler() \
        .checkpoint_path() \
        .flash() \
        .steps() \
        .cfg_scale() \
        .low_vram() \
        .force_cpu() \
        .cuda_device() \
        .num_images() \
        .seed() \
        .output_metadata() \
        .parse()

    # Hard coded prompts
    arg_prompt = r"chibi, waifu, scifi, side scrolling, character, side scrolling, white background, centered," \
             r" full character, no background, not centered, line drawing, sketch, black and white," \
             r" colored, offset, video game,exotic, sureal, miltech, fantasy, frank frazetta," \
             r" terraria, final fantasy, cortex command, surreal, water color expressionist, david mckean, " \
             r" jock, esad ribic, chris bachalo, expressionism, Jackson Pollock, Alex Kanevskyg, Francis Bacon, Trash Polka," \
             r" abstract realism, andrew salgado, alla prima technique, alla prima, expressionist alla prima, expressionist alla prima technique"


    prompts = [arg_prompt]

    # Split the numbers_string into a list of substrings using the comma as the delimiter
    seed_string_array = opt.seed.split(',')

    # Convert the elements in the list to integers (optional, if needed)
    seed_array = [int(num) for num in seed_string_array]

    if len(seed_array) == 0:
        seed_array = [0]

    # timestamp = datetime.now().strftime('%d-%m-%Y-%H-%M-%S')
    # filename = os.path.join(opt.output, f'{timestamp}.jpg')

    # Set flash attention
    CrossAttention.use_flash_attention = opt.flash

    # Starts the text2img
    txt2img = Txt2Img(
        sampler_name=opt.sampler,
        n_steps=opt.steps,
        force_cpu=opt.force_cpu,
        cuda_device=opt.cuda_device,
    )
    txt2img.initialize_latent_diffusion(autoencoder=None, clip_text_embedder=None, unet_model=None,
                                        path=opt.checkpoint_path, force_submodels_init=True)

    with monit.section('Generate', total_steps=len(prompts)) as section:
        for prompt in prompts:

            prompt_list = prompt.split(',');

            for i in range(opt.num_images):
                this_prompt = ''
                this_prompt_list = []
                num_prompts_per_image = 12
                while num_prompts_per_image > 0:
                    random_index = random.randint(0, len(prompt_list) - 1)
                    chosen_string = prompt_list[random_index]
                    if not chosen_string in this_prompt_list:
                        this_prompt_list.append(chosen_string)
                        num_prompts_per_image = num_prompts_per_image - 1

                for prompt_item in this_prompt_list:
                    this_prompt = this_prompt + prompt_item + ', '

                print("Generating image " + str(i) + " out of " + str(opt.num_images));
                start_time = time.time()
                timestamp = datetime.now().strftime('%d-%m-%Y-%H-%M-%S')
                image_name = f'{timestamp}-{i}.jpg'
                filename = os.path.join(opt.output, image_name)

                this_seed = seed_array[i % len(seed_array)]

                images = txt2img.generate_images(
                    batch_size=opt.batch_size,
                    prompt=this_prompt,
                    uncond_scale=opt.cfg_scale,
                    low_vram=opt.low_vram,
                    seed=this_seed,
                )


                print(images.shape)
                image_list, image_hash_list = save_images(images, filename)
                image_hash = image_hash_list[0]
                image = image_list[0]

                un_cond, cond = txt2img.get_text_conditioning(opt.cfg_scale, prompts, opt.batch_size)
                # Convert the tensor to a flat vector
                # cond = torch.flatten(cond)

                # convert tensor to numpy array
                with torch.no_grad():
                    embedded_vector = cond.cpu().numpy()

                # get image features
                image_features = get_image_features(image, device=opt.cuda_device)

                # hard coded for now
                chad_score_model_path = "input/model/chad_score/chad-score-v1.pth"
                chad_score_model_name = os.path.basename(chad_score_model_path)

                # compute chad score
                chad_score = get_chad_score(image_features, chad_score_model_path, device=opt.cuda_device)

                # get numpy list from image_features
                with torch.no_grad():
                    image_features_numpy = image_features.cpu().numpy()

                generation_task_result = GenerationTaskResult(embedded_vector, [], image_name, image_hash, [], image_features_numpy,
                                                              chad_score_model_name, chad_score.item(), this_seed, opt.cfg_scale)




                # Save the data to a JSON file
                json_filename = os.path.join(opt.output, f'{timestamp}-{i}.json')
                generation_task_result.save_to_json(json_filename);

                # Capture the ending time
                end_time = time.time()

                # Calculate the execution time
                execution_time = end_time - start_time

                print("Execution Time:", execution_time, "seconds")



if __name__ == "__main__":
    main()
