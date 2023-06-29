import time
import discord
from dotenv import load_dotenv
import requests
import os
from image_detector.image_detector import ImageDetector
import shutil


class MyClient(discord.Client):
    messages_bot = {}

    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def on_message(self, message):
        print('Message from {0.author}: {0.content}'.format(message))
        channel = message.channel
        curr_time = time.strftime("%Y%m%d-%H%M%S")
        folder_name = './image_detector/' + \
            str(message.channel.id) + "_" + message.author.name+"_"+curr_time

        dir_path = os.path.dirname(os.path.realpath(__file__))
        os.chdir(dir_path)

        if message.attachments and message.author != self.user and message.content == "TRADE":
            i = 0

            if message.author.dm_channel is None:
                await message.author.create_dm()

                self.messages_bot[message.id] = [await channel.send(content="A processar... Por favor checa a tua DM para mais informação", reference=message),]
            for att in message.attachments:
                if 'image' in att.content_type:
                    if not os.path.exists(folder_name):
                        os.mkdir(folder_name)
                    if not os.path.exists(folder_name+'/pics'):
                        os.mkdir(folder_name+'/pics')
                    r = requests.get(att.url, allow_redirects=True)
                    open(folder_name+'/pics/' + str(i) +
                         '.jpeg', 'wb').write(r.content)
                    print("Ficheiro de " + message.author.name + " recebido")
                    i += 1
            await message.author.dm_channel.send(content="A processar...")
            id = ImageDetector(message.channel.id,
                               message.author.name, curr_time, folder_name)
            results = id.results()
            await message.author.dm_channel.send(content="Processamento terminado")
            if results > 0:
                await message.author.dm_channel.send(str(results) + " Resultados Encontrados")
                for folder in os.listdir(folder_name+'/results'):
                    files = {}
                    for file in os.listdir(folder_name+'/results/'+folder):
                        autor = file.split("_")[0]
                        if autor != message.author.name:
                            if autor in files:
                                files[autor].append(discord.File(
                                    folder_name+'/results/'+folder+'/'+file))
                            else:
                                files[autor] = [discord.File(
                                    folder_name+'/results/'+folder+'/'+file),]
                    for autor in files:
                        await message.author.dm_channel.send(content="Negoceia com @"+autor, files=files[autor])
            else:
                await message.author.dm_channel.send("Nenhum resultado encontrado")
            shutil.rmtree(folder_name)


intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)


load_dotenv()
token = os.getenv('DISCORD_TOKEN')
client.run(token)
