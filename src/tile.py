#%%
import os
import math
import urllib
import random

from settings import TILE_FOLDER
import utils.coord_transform as ct
from utils.image_process import merge_tiles, clip_background


class Tiles():
    def __init__(self, folder, map_provider='amap'):
        self.folder = os.path.join(folder, map_provider)
        self.provider = map_provider
        
        self.lyrs = {
            'amap':{
                's': 6,
                'm': 7,
                't': 8,
            },
            'osm':{
                "s":'s'
            }
        }
        
        self.url_dict = {
            'amap': "https://webst01.is.autonavi.com/appmaptile?style={lyrs}&x={x}&y={y}&z={z}", # GCJ02, zoom 最大值为18
            'osm': "https://b.tile.openstreetmap.org/{z}/{x}/{y}.png", # WGS84
            'local': "http://192.168.135.15:4000/tile?z={z}&x={x}&y={y}"
        }
        self.base_url = self.url_dict[map_provider]

        self.header = {
            # 'Host': 'tile.openstreetmap.org',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36 Edg/93.0.961.44',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            # ':authority':'b.tile.openstreetmap.org'
            # 'Cookie': '1P_JAR=2018-12-05-01; NID=148=D5yxfc0ZCd0e5ud8-h_zkKzgwBNnf613_Jhyjin7ixp6KmFKWgoWD5unzeJjfMsLRNQw2-3YwPDqN-JqACYsR5Zfuqj7h0qgzFbCD8S-oCWXrV8MSCZGMRP1uJMNuhhSjlhznjWResA5VzIYk61w5ALpDAUqRM0_wvP_t8dIjJA',
        }

        pass


    def tileXY_To_lnglat(self, tileX, tileY, ZOOM, in_sys='wgs', out_sys='wgs'):
        # 就算是Google地图，坐标也是GCJ02
        lng = tileX/pow(2,ZOOM)*360-180
        lat = math.atan( math.sinh( math.pi - 2*math.pi*( (tileY)/pow(2,ZOOM) ) ) )* 180/math.pi
        if in_sys == 'gcj' and out_sys == 'wgs':
            lng,lat = ct.gcj02_to_wgs84(lng,lat)
            
        return "%.7f, %.7f"%(lng,lat)


    def tileXYToLnglat(self, x, y, zoom):
        lng = x/math.pow(2,zoom)*360-180
        lat = math.atan(math.sinh(math.pi-2*math.pi*y/math.pow(2,zoom))) * 180 /math.pi
        
        return round(lng, 6), round(lat, 6)


    def lnglatToTileXY(self, lng,lat,zoom):
        tileX = math.floor((lng+180)/360 * pow(2,zoom))
        tileY = math.floor( (0.5 -( math.log( math.tan( lat * math.pi / 180) + ( 1/math.cos( lat*math.pi /180)) , math.e) /2/math.pi) )* pow(2,zoom))
        
        return tileX, tileY

    
    def get_tile(self, z, x, y, lyrs='s', rewrite=False):
        """
        @params: lyrs m：路线图; t：地形图; p：带标签的地形图; s：卫星图; y：带标签的卫星图; h：标签层（路名、地名等）; 
        folder: out folder
        """
        file_dir = os.path.join( self.folder, f'{lyrs}/{z}/{x}/' )
        if not os.path.isdir(file_dir):
            os.makedirs(file_dir)

        file_path = os.path.join( file_dir, f'{y}.jpg' )
        if os.path.isfile(file_path) and not rewrite:
            return file_path
        
        url = self.base_url.format(x=x, y=y, z=z, lyrs=self.lyrs[self.provider][lyrs])

        # headers= self.send_headers[random.randint(0,len(self.send_headers)-1)]
        request = urllib.request.Request(url=url, method='GET', headers=self.header)
        print(url)
        img = urllib.request.urlopen(request)

        f = open(file_path, 'wb')
        f.write(img.read())
        f.flush()
        f.close()
        
        return file_path


    def get_tiles_by_bbox(self, bbox, z=18, lyrs='s', in_sys='wgs'):
        """
        @param: bbox = [left, upper, right, lower], example: [113.93623972, 22.5425676, 113.93823028, 22.5426534]
        @param: in_sys: input coordinations system, while the output is gcj02
        @return: the files list of tiles, and the bbox [left, upper, right, lower] of these tiles (in the 'in_sys' coordination system)
        """
        if in_sys =='wgs':
            bbox = [*ct.wgs84_to_gcj02( *bbox[:2] ), *ct.wgs84_to_gcj02( *bbox[2:] )]

        (tile_x0, tile_y0), (tile_x1, tile_y1) = self.lnglatToTileXY(*bbox[:2], z), self.lnglatToTileXY(*bbox[2:], z)

        bbox = [*self.tileXYToLnglat(tile_x0, tile_y0, z), *self.tileXYToLnglat(tile_x1+1, tile_y1+1, z)]
        
        if in_sys =='wgs':
            bbox = [*ct.gcj02_to_wgs84( *bbox[:2] ), *ct.gcj02_to_wgs84( *bbox[2:] )]
            
        tiles_lst = []
        for x in range( tile_x0, tile_x1+1):
            for y in range( tile_y0, tile_y1+1):
                f = self.get_tile( x=x, y=y, z=z, lyrs=lyrs)
                tiles_lst.append(f)


        return tiles_lst, bbox


    def tile_background(self, bbox, zoom, in_sys='wgs'):
        lst, img_bbox = self.get_tiles_by_bbox(bbox, zoom, in_sys=in_sys)
        to_image        = merge_tiles(lst)
        background, _   = clip_background( to_image, img_bbox, bbox, False)
        
        return background


#%%

if __name__ == '__main__':

    tile = Tiles(TILE_FOLDER, map_provider='osm')
    tile.get_tile(15,26752,14249)


    tile = Tiles(TILE_FOLDER, map_provider='amap')
    futian = (114.05097,   22.54605,  114.05863,   22.53447)
    # bbox = [113.931914,  22.580613, 113.944456, 22.573536]
    tile.tile_background(futian, 18)

# %%
