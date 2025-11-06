import os
import json
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import pillow_heif
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
import warnings
warnings.filterwarnings('ignore')

class PhotoMetadataExtractor:
    def __init__(self, image_path):
        self.image_path = image_path
        self.metadata = {}
        
    def extract_basic_info(self):
        """Ekstrak informasi dasar gambar"""
        try:
            with Image.open(self.image_path) as img:
                self.metadata['Basic_Info'] = {
                    'Format': img.format,
                    'Mode': img.mode,
                    'Size': img.size,
                    'Width': img.width,
                    'Height': img.height,
                    'Filename': os.path.basename(self.image_path),
                    'File_Size': f"{os.path.getsize(self.image_path)} bytes"
                }
        except Exception as e:
            self.metadata['Basic_Info'] = {'Error': str(e)}
    
    def extract_exif_data(self):
        """Ekstrak data EXIF dari gambar"""
        try:
            with Image.open(self.image_path) as img:
                exif_data = img._getexif()
                
                if exif_data:
                    exif_dict = {}
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)
                        
                        # Handle GPS info separately
                        if tag == 'GPSInfo':
                            gps_data = self.extract_gps_info(value)
                            exif_dict[tag] = gps_data
                        else:
                            # Convert bytes to string if necessary
                            if isinstance(value, bytes):
                                try:
                                    value = value.decode('utf-8', errors='ignore')
                                except:
                                    value = str(value)
                            exif_dict[tag] = value
                    
                    self.metadata['EXIF_Data'] = exif_dict
                else:
                    self.metadata['EXIF_Data'] = {'Info': 'No EXIF data found'}
                    
        except Exception as e:
            self.metadata['EXIF_Data'] = {'Error': str(e)}
    
    def extract_gps_info(self, gps_info):
        """Ekstrak dan konversi data GPS"""
        gps_data = {}
        try:
            for key in gps_info.keys():
                value = gps_info[key]
                tag = GPSTAGS.get(key, key)
                
                if tag == 'GPSLatitude':
                    gps_data['Latitude'] = self.convert_to_degrees(value)
                    gps_data['LatitudeRef'] = gps_info.get(1, 'Unknown')
                elif tag == 'GPSLongitude':
                    gps_data['Longitude'] = self.convert_to_degrees(value)
                    gps_data['LongitudeRef'] = gps_info.get(3, 'Unknown')
                elif tag == 'GPSAltitude':
                    gps_data['Altitude'] = f"{float(value)} meters"
                elif tag == 'GPSTimeStamp':
                    gps_data['GPSTime'] = str(value)
                else:
                    gps_data[tag] = value
            
            # Create Google Maps link if coordinates available
            if 'Latitude' in gps_data and 'Longitude' in gps_data:
                lat = gps_data['Latitude']
                lon = gps_data['Longitude']
                if gps_data.get('LatitudeRef') == 'S':
                    lat = -lat
                if gps_data.get('LongitudeRef') == 'W':
                    lon = -lon
                
                gps_data['Google_Maps_Link'] = f"https://maps.google.com/?q={lat},{lon}"
                
        except Exception as e:
            gps_data['Error'] = str(e)
            
        return gps_data
    
    def convert_to_degrees(self, value):
        """Konversi koordinat GPS ke derajat desimal"""
        try:
            d, m, s = value
            return d + (m / 60.0) + (s / 3600.0)
        except:
            return str(value)
    
    def extract_heic_metadata(self):
        """Ekstrak metadata khusus untuk format HEIC"""
        try:
            if self.image_path.lower().endswith(('.heic', '.heif')):
                heif_file = pillow_heif.read_heif(self.image_path)
                metadata = {}
                
                for metadata_item in heif_file.metadata:
                    metadata[metadata_item['type']] = metadata_item['data']
                
                self.metadata['HEIC_Metadata'] = metadata
        except Exception as e:
            self.metadata['HEIC_Metadata'] = {'Error': str(e)}
    
    def extract_file_metadata(self):
        """Ekstrak metadata file system"""
        try:
            stat_info = os.stat(self.image_path)
            file_metadata = {
                'Creation_Time': stat_info.st_ctime,
                'Modification_Time': stat_info.st_mtime,
                'Access_Time': stat_info.st_atime,
                'File_Permissions': stat_info.st_mode,
                'File_Inode': stat_info.st_ino
            }
            self.metadata['File_System_Data'] = file_metadata
        except Exception as e:
            self.metadata['File_System_Data'] = {'Error': str(e)}
    
    def display_metadata(self):
        """Tampilkan semua metadata yang berhasil diekstrak"""
        print("=" * 70)
        print(f"METADATA EKSTRAKSI UNTUK: {self.image_path}")
        print("=" * 70)
        
        for category, data in self.metadata.items():
            print(f"\n{category}:")
            print("-" * 40)
            
            if isinstance(data, dict):
                for key, value in data.items():
                    if key in ['Google_Maps_Link']:
                        print(f"  {key}: \033[94m{value}\033[0m")  # Blue color for links
                    elif 'GPS' in key or 'Location' in key:
                        print(f"  {key}: \033[92m{value}\033[0m")  # Green color for GPS
                    else:
                        print(f"  {key}: {value}")
            else:
                print(f"  {data}")
    
    def save_to_json(self, output_file=None):
        """Simpan metadata ke file JSON"""
        if output_file is None:
            output_file = os.path.splitext(self.image_path)[0] + '_metadata.json'
        
        try:
            # Convert non-serializable objects to string
            serializable_metadata = {}
            for category, data in self.metadata.items():
                if isinstance(data, dict):
                    serializable_metadata[category] = {}
                    for key, value in data.items():
                        try:
                            json.dumps(value)  # Test if serializable
                            serializable_metadata[category][key] = value
                        except:
                            serializable_metadata[category][key] = str(value)
                else:
                    serializable_metadata[category] = str(data)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_metadata, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ Metadata disimpan ke: {output_file}")
            
        except Exception as e:
            print(f"❌ Error menyimpan ke JSON: {e}")
    
    def extract_all(self):
        """Jalankan semua proses ekstraksi"""
        print(f"🔍 Memproses file: {self.image_path}")
        
        self.extract_basic_info()
        self.extract_exif_data()
        self.extract_heic_metadata()
        self.extract_file_metadata()
        
        self.display_metadata()
        return self.metadata

# Fungsi utama
def main():
    # Ganti dengan path foto Anda
    photo_path = input("Masukkan path foto yang ingin dianalisis: ").strip().strip('"')
    
    if not os.path.exists(photo_path):
        print("❌ File tidak ditemukan!")
        return
    
    # Inisialisasi extractor
    extractor = PhotoMetadataExtractor(photo_path)
    
    # Jalankan ekstraksi
    metadata = extractor.extract_all()
    
    # Tanya user apakah ingin menyimpan ke JSON
    save_choice = input("\n💾 Simpan metadata ke file JSON? (y/n): ").lower()
    if save_choice == 'y':
        extractor.save_to_json()

if __name__ == "__main__":
    main()
