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

        if message.author != self.user and message.content == "TRADE":
            try:
                i = 0

                if message.author.dm_channel is None:
                    await message.author.create_dm()

                self.messages_bot[message.id] = [await channel.send(content="Processing... Please check your DM's", reference=message),]
                await message.author.dm_channel.send(content="Processing...")
                if not os.path.exists(folder_name):
                    os.mkdir(folder_name)
                    for att in message.attachments:
                        if 'image' in att.content_type:
                            if not os.path.exists(folder_name+'/pics'):
                                os.mkdir(folder_name+'/pics')
                            r = requests.get(att.url, allow_redirects=True)
                            open(folder_name+'/pics/' + str(i) +
                                '.jpeg', 'wb').write(r.content)
                            print("Ficheiro de " + message.author.name + " recebido")
                            i += 1
                id = ImageDetector(message.channel.id,
                                message.author.name, curr_time, folder_name,len(message.attachments)>0)
                results = id.results()
                await message.author.dm_channel.send(content="Done!")
                if results > 0:
                    await message.author.dm_channel.send(str(results) + " Results found")
                    for folder in os.listdir(folder_name+'/results'):
                        files = {}
                        for file in os.listdir(folder_name+'/results/'+folder):
                            autor = file.split("_")[0]
                            if 'top' not in file:
                                if autor in files:
                                    files[autor].append(discord.File(
                                        folder_name+'/results/'+folder+'/'+file))
                                else:
                                    files[autor] = [discord.File(
                                        folder_name+'/results/'+folder+'/'+file),]
                        for autor in files:
                            if autor != message.author.name:
                                await message.author.dm_channel.send(content="Trade with @"+autor+":", files=files[autor])
                            else:
                                await message.author.dm_channel.send( content="You got:",files=files[autor])
                else:
                    await message.author.dm_channel.send("No results found")
                shutil.rmtree(folder_name)
            except Exception as e:
                await message.author.dm_channel.send("Error, please try again later")
                print(e)    
                if os.path.exists(folder_name):
                    shutil.rmtree(folder_name)


intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)


load_dotenv()
token = os.getenv('DISCORD_TOKEN')
client.run(token)
