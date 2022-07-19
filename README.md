# GBIF downloader

GBIF downloader uses the GBIF API (superb [beginners guide here](https://data-blog.gbif.org/post/gbif-api-beginners-guide/)) to find occurrence records with image data for a given species, genus or broad family name. With this data, GBIF downloader will create a dataframe containing information about a given occurrence, such as species, license, references, image size (exracted from file header, max 1024 bytes downloaded) and image dimensions.

Records can also be filtered based on their types, so you can preferentially download a "MATERIAL_SAMPLE" rather than a "HUMAN_OBSERVATION".

GBIF downloader renames each downloaded file uniquely with UUID to avoid overwrites. Though be careful since if you choose to download the same dataframe again, you'll duplicate your images.