import urllib
import json
import requests
import pandas as pd
import os
import uuid
import random
from PIL import ImageFile

class GBIFImages:
    def __init__(
            self, 
            species, 
            limit, 
            get_image_info=True, 
            record_type=None, 
            save_dir=None,
            img_num_per_record=1
        ):
        """
        If get_image_info == True, only records with image information
        will be returned.
        limit: Number of occurrence records to find
        basisOfRecord: None, "MATERIAL_SAMPLE", or "HUMAN_OBSERVATION"

        img_num_per_record: if a record has multiple images, how many 
        images should be taken (records with multiple images may lead to duplicates).
        Otherwise, x number of images will be randomly sampled
        """

        self.species = species
        self.limit = limit
        self.get_image_info = get_image_info
        self.record_type = record_type
        self.save_dir = save_dir
        self.img_num_per_record = img_num_per_record

    def get_occurrence_info(self):
        """
        For a given species list, return a pd.DataFrame containing
        info such as link, lisence and date

        limit: the number of occurences to call from the API. However, 
        not all occurrences will have an image
        """
        df_list = list()
        if isinstance(self.species, str): self.species = [self.species]
        # Make spaces url friendly
        self.species = [org.replace(" ", "%20") for org in self.species]
        for i in self.species:
            species_key = self.get_taxon_key(i)
            self.api_url = self.build_gbif_api_request(species_key)
            json = self.get_json()
            df = self.extract_json_image_info(json)
            df_list.append(df)
        df_list = pd.concat(df_list, ignore_index=True)
        return df_list

    def save_images(self, img_dataframe):
        """
        For a GBIF DataFrame, download the images.
        Filenames after the species name and occurrence ID.

        Filenames will contain with a UUID
        """
        if not os.path.isdir(self.save_dir):
            os.mkdir(self.save_dir)

        # img = "https://inaturalist-open-data.s3.amazonaws.com/photos/74623021/original.jpg"
        for ind, species, img_url in zip(img_dataframe.index, img_dataframe["species"], img_dataframe["identifier"]):
            id = uuid.uuid4()
            filename = f"{species}-{id}-{img_url.split('/')[-1]}"
            file_path = os.path.join(self.save_dir, filename)
            img_request = requests.get(img_url)
            with open(file_path, "wb") as f:
                print(f"saving as {filename}")
                f.write(img_request.content)
            img_dataframe.loc[ind, "local_img_path"] = file_path
        return img_dataframe

    def get_sizes(self, url):
        """
        Find image dimensions and file size without downloading
        From: https://stackoverflow.com/questions/7460218/get-image-size-without-downloading-it-in-python
        """
        # get file size *and* image size (None if not known)
        img = urllib.request.urlopen(url)
        size = img.headers.get("content-length")
        if size: 
            size = int(size)
        p = ImageFile.Parser()
        while True:
            # Read the first 1024 bytes to get the fileheader
            data = img.read(1024)
            if not data:
                break
            # Feed the image to the PIL parser to get header info
            p.feed(data)
            if p.image:
                # get the image size (Width, Height)
                # image.size = (width, height)
                return size, p.image.size
                break
        img.close()
        return(size, None)
            
    def get_taxon_key(self, species):
        """
        For a given species, find the corresponding
        taxon key on GBIF
        """
        gbif_species_base = "https://api.gbif.org/v1/species/match?"
        api_url = f"{gbif_species_base}name={species}"

        with urllib.request.urlopen(api_url) as url:
            data = json.loads(url.read().decode())
        return data["usageKey"]
        
    def build_gbif_api_request(self, species):
        """
        Create a GBIF API request for a given species.
        Can also specific if to filter for images.
        """
        gbif_api_base = "https://api.gbif.org/v1/occurrence/search?"
        
        if self.limit is not None and isinstance(self.limit, int):
            limit_api = f"&limit={self.limit}"
        else:
            limit_api = ""

        if self.get_image_info:
            api_img = "media_type=StillImage"
        else:
            api_img = ""

        if self.record_type is not None and self.record_type in ["MATERIAL_SAMPLE", "HUMAN_OBSERVATION"]:
            basisOfRecord = f"&basisOfRecord={self.record_type}"
        else:
            basisOfRecord = ""
        
        url = f"{gbif_api_base}{api_img}&taxon_key={species}{limit_api}{basisOfRecord}"
        
        print(url)
        return url

    def get_json(self):
        with urllib.request.urlopen(self.api_url) as url:
            data = json.loads(url.read().decode())
        return data

    def extract_json_image_info(self, json):
        """
        For a JSON downloaded with the GBIF API,
        extract image information such as lisence 
        and image url

        img_num_per_record: if there are multiple images for one record,
        randomly select 1. This avoids duplicate or visually similar images
        being included
        """
        output_df = list()

        data_columns = ["species", "sex", "taxonKey", "basisOfRecord"]

        if len(json["results"]) == 0:
            print("--- Found no records ---")
            return pd.DataFrame()
        
        num_records = (len(json["results"]) if not None else 0)

        print(f"--- Found {num_records} records ---")

        for data in json["results"]:
            for record in data["extensions"]:
                # list to hold multiple copies in one record
                # ie. multiple images for the same occurrence ID
                # also ie. image duplicates or visually similar images
                record_df_list = list()
                if "Multimedia" in record:
                    for image_info in data["extensions"][record]:
                        df_dict = pd.DataFrame({k.split("/")[-1]:[v] for k,v in image_info.items()})
                        # Some records to not have species info
                        for i in data_columns:
                            if i not in data.keys():
                                df_dict[i] = [None]
                            else:
                                df_dict[i] = [data[i]]
                        df_dict["api_url"] = [self.api_url]
                        # Remove records with missing species information
                        record_df_list.append(df_dict)
                    if len(record_df_list) != self.img_num_per_record:
                        # If multiple images were found for one record, randomly select one
                        # I know this isn't ideal, but there are a lot of duplicates
                        # How else can you reasonably decide over a huge quantity of images?
                        # The alternative is to potential have >5 duplicates of the same image
                        # Long live stochasticism
                        record_df_list = random.sample(record_df_list, k=self.img_num_per_record)
                    record_df = pd.concat(record_df_list, axis=0, ignore_index=True)
                    record_df["image_file_size_MB"] = [self.get_sizes(record_df.loc[:,"identifier"][0])[0] / 1e6]
                    record_df["image_dimensions_WxH"] = [self.get_sizes(record_df.loc[:,"identifier"][0])[1]]
                    # print("!!!", df_dict.loc[:,"identifier"][0])
                    # Concat before append as append alone seems to transform DataFrame to list
                    # Unsure why.
                    output_df.append(record_df)
                if "Multimedia" not in record:
                    pass
        output_df = pd.concat(output_df, axis=0, ignore_index=True)
        # Take only images with a license and a recorded species name
        output_df = output_df[
                (output_df["license"].notna()) & 
                (output_df["species"].notna())
            ]
        return output_df
        
    def download_images(self):
        # df = self.get_occurrence_info(self.species, self.limit, self.record_type)
        df = self.get_occurrence_info()
        if self.save_dir is not None:
            df = self.save_images(df)
        total_size = df["image_file_size_MB"].sum() / 1e3 
        print(f"Total size of images in this dataset: {total_size} GB")
        return df