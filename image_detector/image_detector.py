import cv2
import numpy as np
import os
from PIL import Image
from PIL import ImageChops
import sqlite3
import shutil
import time

db_name = 'image_detector.sqlite'

dir_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(dir_path)

con = sqlite3.connect(db_name)


class ImageDetector():
	def __init__(self, channel, author, date, folder):
		init_database()
		self.channel = channel
		self.author = author
		self.date = date
		self.folder = folder
		os.chdir(self.folder)

		cur = con.cursor()

		if cur.execute('''SELECT name FROM channel WHERE name = ? AND author = ?''', (channel, author)).fetchone() is None:
			cur.execute(
				'''INSERT INTO channel (name, author) VALUES (?, ?)''', (channel, author))

		con.commit()

		self.prepare_img()
		self.organize_imgs()

	def prepare_img(self):
		cur = con.cursor()
		if not os.path.exists('./tmp/'):
			os.mkdir('./tmp/')
		pics = os.listdir('./pics/')
		for pic in pics:
			img = cv2.imread('./pics/' + pic)

			gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
			gray = cv2.GaussianBlur(gray, (5, 5), 20)
			cv2.imwrite('./tmp/gray.jpeg', gray)
			edged = cv2.Canny(gray, 20, 50)
			(cnts, _) = cv2.findContours(edged.copy(),
										 cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
			cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:1]

			for c in cnts:
				rect = cv2.minAreaRect(c)
				box = cv2.boxPoints(rect)
				box = np.int0(box)

			x, y, w, h = cv2.boundingRect(c)
			crop_img = img[y:y+h, x:x+w]
			crop_img = cv2.resize(crop_img, (750, 1500))

			cv2.imwrite('./tmp/' + pic, crop_img)

			with open('./tmp/' + pic, 'rb') as f:
				photo = f.read()

			cur.execute('''INSERT INTO image (channel_id, author_name, date, photo) VALUES (?, ?, ?, ?)''',
						(self.channel, self.author, self.date, photo))
		con.commit()
		shutil.rmtree('./tmp/')

	def organize_imgs(self):
		cur = con.cursor()
		old_pics = cur.execute(
			'''SELECT photo,type,author_name FROM image WHERE channel_id = ? AND date < ? AND type NOT NULL''', (self.channel, self.date)).fetchall()

		curr_pics = cur.execute('''SELECT photo FROM image WHERE channel_id = ? AND author_name = ? AND date = ?''',
								(self.channel, self.author, self.date)).fetchall()

		if not os.path.exists('./tmp/'):
			os.mkdir('./tmp/')

		max_type = 0
		for curr_pic in curr_pics:
			if old_pics == []:
				cur.execute('''UPDATE image SET type = ? WHERE photo = ?''',
							(max_type+1, curr_pic[0]))
				max_type += 1
				continue
			for old_pic in old_pics:
				if curr_pic != old_pic:

					with open('./tmp/curr_pic.jpeg', 'wb') as f:
						f.write(curr_pic[0])

					with open('./tmp/old_pic.jpeg', 'wb') as f:
						f.write(old_pic[0])

					img_curr = cv2.imread('./tmp/curr_pic.jpeg')
					img_old = cv2.imread('./tmp/old_pic.jpeg')
					sub = cv2.subtract(img_old, img_curr)
					total_pixels = sub.shape[0] * sub.shape[1]
					white_pixels = np.sum(sub >= 50)
					print("Confidence-> "+str(white_pixels / total_pixels))
					if ((white_pixels / total_pixels) <= 0.15):
						if old_pic[2] == self.author:
							cur.execute('''DELETE FROM image WHERE photo = ? AND date < ?''',
										(old_pic[0], self.date))

						cur.execute('''UPDATE image SET type = ? WHERE photo = ?''',
									(old_pic[1], curr_pic[0]))
						break
			else:
				max_type = cur.execute(
					'''SELECT MAX(type) FROM image WHERE channel_id = ?''', (self.channel,)).fetchone()[0]
				if max_type is None:
					max_type = 0
				cur.execute('''UPDATE image SET type = ? WHERE photo = ?''',
							(max_type + 1, curr_pic[0]))
			con.commit()
		shutil.rmtree('./tmp/')

	def find_differences(self):
		cur = con.cursor()
		if not os.path.exists('./results/'):
			os.mkdir('./results/')

		curr_pics = cur.execute('''SELECT photo,type FROM image WHERE channel_id = ? AND author_name = ? AND date = ?''',
								(self.channel, self.author, self.date)).fetchall()

		if not os.path.exists('./tmp/'):
			os.mkdir('./tmp/')

		results = 0

		for curr_pic in curr_pics:
			tester_pics = cur.execute('''SELECT photo, author_name FROM image WHERE channel_id = ? AND type = ? AND author_name != ?''',
									  (self.channel, curr_pic[1], self.author)).fetchall()

			with open('./tmp/curr_pic.jpeg', 'wb') as f:
				f.write(curr_pic[0])

			curr = Image.open('./tmp/curr_pic.jpeg')
			cut = True
			count = 0
			for tester_pic in tester_pics:
				if not os.path.exists('./results/' + str(curr_pic[1])):
					os.mkdir('./results/' + str(curr_pic[1]))
				with open('./tmp/tester_pic.jpeg', 'wb') as f:
					f.write(tester_pic[0])

				tester = Image.open('./tmp/tester_pic.jpeg')

				diff = ImageChops.difference(curr, tester)

				if (cut):
					# Crop top
					box = (10, diff.size[1] / 5, diff.size[0] -
						   10, diff.size[1]-diff.size[1]/15)
					diff = diff.crop(box)
					curr = curr.crop(box)
					tester = tester.crop(box)
					curr.save(
						'./results/' + str(curr_pic[1]) + '/' + self.author + '_top.jpeg')
					tester.save(
						'./results/' + str(curr_pic[1]) + '/' + tester_pic[1] + '_top.jpeg')
					cut = False

				for x in range(3):
					for y in range(3):
						# crop in a 3x3 grid
						box = (x * diff.size[0] / 3, y * diff.size[1] / 3,
							   (x + 1) * diff.size[0] / 3, (y + 1) * diff.size[1] / 3)
						crop = diff.crop(box)
						if (np.sum(np.array(crop))/(crop.size[0]*crop.size[1]) > 100):
							crop = curr.crop(box)
							crop.save('./results/' + str(curr_pic[1]) + '/' + tester_pic[1] + "_" +  str(count) + '_' +
									  str(x) + str(y) + '_0.jpeg')
							crop = tester.crop(box)
							crop.save('./results/' + str(curr_pic[1]) + '/' + tester_pic[1] + '_'+ str(count) + '_' +
									  str(x) + str(y) + '_1.jpeg')
							count += 1
							results += 1

		shutil.rmtree('./tmp/')
		return results

	def results(self):
		res = self.find_differences()
		print("Results for " + self.author +
			  " on " + self.date + " -> " + str(res))
		return res


def init_database():
	cursor = con.cursor()
	cursor.execute('''CREATE TABLE IF NOT EXISTS channel (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		name TEXT NOT NULL,
		author TEXT NOT NULL
	)''')
	cursor.execute('''CREATE TABLE IF NOT EXISTS image (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		channel_id INTEGER NOT NULL,
		author_name INTEGER NOT NULL,
		photo BLOB NOT NULL,
		date DATE NOT NULL,
		type INTEGER,
		FOREIGN KEY(channel_id, author_name) REFERENCES channel(id, author)
	)''')
	con.commit()


"""
if __name__ == '__main__':
	id = ImageDetector('test_channel', 'test_author', time.time(), 'test_folder')

	os.chdir('..')

	id = ImageDetector('test_channel', 'test_author2', time.time(), 'test_folder2')
"""
