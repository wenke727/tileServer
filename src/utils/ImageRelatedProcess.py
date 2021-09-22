import os
import math
import numpy as np
from PIL import Image
from scipy import ndimage
import matplotlib.pyplot as plt
import coordTransform_py.CoordTransform_utils as ct

class imageFile():
    def __init__(self, *args, **kwargs):
        
        pass


def clip_background( img, bb, clip_bb, show = False ):
    """
    clip the tile accroding to the bbox
    @param
        bb: left, upper, right, lower;
        clip_bb: left, upper, right, lower
    @return: the clip image
    """
    x_range, y_range = img.size
    dx, dy = x_range / ( bb[2]-bb[0] ), y_range / ( bb[3]-bb[1] )
    
    [x0, y0, x1, y1] = clip_bb
    x0_pix = int((x0 - bb[0]) * dx)
    y0_pix = int((y0 - bb[1]) * dy)
    x1_pix = int((x1 - bb[0]) * dx)
    y1_pix = int((y1 - bb[1]) * dy)

    cropped = img.crop((x0_pix,y0_pix,x1_pix,y1_pix))  # (left, upper, right, lower)
    # cropped.save("pil_cut_thor.jpg")
    BB = [ clip_bb[0],clip_bb[2], clip_bb[3],clip_bb[1] ]
    if show:
        fig, ax = plt.subplots(1,1)
        ax.imshow( cropped, zorder=0, extent=clip_bb )
    return cropped, BB


def merge_tiles(f_lst, file_name_catalog = True):
    """
    merge tiles into one
    @param: f_lst: tiles list
    @param: the catalog type that store in the system
    @return: the merge tile
    """
    xs, ys = [], []
    z_folder =  '/'.join( f_lst[0].split('/')[:-2])

    if file_name_catalog:
        for filename in f_lst:
            items = filename.replace('.jpg', '').split('/')
            z, x, y = [int(i) for i in items[-3:]]
            if x not in xs:
                xs.append(x)
            if y not in ys:
                ys.append(y)

    # 定义图像拼接函数
    IMAGE_SIZE = 256
    max_x, min_x, max_y, min_y = max(xs), min(xs), max(ys), min(ys)
    IMAGE_COLUMN = max_x - min_x + 1
    IMAGE_ROW    = max_y - min_y + 1
    to_image = Image.new('RGB', (IMAGE_COLUMN * IMAGE_SIZE, IMAGE_ROW * IMAGE_SIZE))

    for x in xs:
        for y in ys:
            path = os.path.join( z_folder, f'{x}/{y}.jpg')
            try:
                from_image = Image.open( path ).resize( (IMAGE_SIZE, IMAGE_SIZE), Image.ANTIALIAS)
                to_image.paste( from_image, ((x - min_x ) * IMAGE_SIZE, (y - min_y) * IMAGE_SIZE) )
            except:
                print(f"数据缺失: {path}")
                pass

    return to_image


def tile_gcj02_to_wgs84(tile_x, tile_y, zoom, origin_path ='/home/pcl/Data/tile/shenzhen/s/', des_path='/home/pcl/Data/tile/shenzhen/wgs'):
    """
    transfer the tile coordination systen from gcj02 to wgs84
    @para: tile_x, tile_y, zoom
    """
    bbox_wgs = [*tileXYToLnglat( tile_x, tile_y, zoom ), *tileXYToLnglat( tile_x+1, tile_y+1, zoom )]
    bbox_gcj = [*ct.wgs84_to_gcj02( bbox_wgs[0], bbox_wgs[1] ), *ct.wgs84_to_gcj02( bbox_wgs[2], bbox_wgs[3] )]

    min_x, min_y = lnglatToTileXY(*bbox_gcj[:2], zoom)
    max_x, max_y = lnglatToTileXY(*bbox_gcj[2:], zoom)
    bbox_img     = [*tileXYToLnglat(min_x, min_y, zoom), *tileXYToLnglat(max_x+1, max_y+1, zoom)]

    IMAGE_SIZE = 256
    IMAGE_COLUMN = max_x - min_x + 1
    IMAGE_ROW    = max_y - min_y + 1
    to_image = Image.new('RGB', (IMAGE_COLUMN * IMAGE_SIZE, IMAGE_ROW * IMAGE_SIZE))
    
    for x in range( min_x, max_x + 1):
        for y in range( min_y, max_y+1 ):
            path = os.path.join( origin_path, f'{zoom}/{x}/{y}.jpg')
            try:
                from_image = Image.open( path ).resize( (IMAGE_SIZE, IMAGE_SIZE), Image.ANTIALIAS)
                to_image.paste( from_image, ((x - min_x ) * IMAGE_SIZE, (y - min_y) * IMAGE_SIZE) )
            except:
                print(f"数据缺失: {path}")
                pass

    img, _ = clip_background(to_image, bbox_img, bbox_gcj)

    if des_path:
        file_dir = os.path.join( des_path, f'{zoom}/{tile_x}/' )
        if not os.path.isdir(file_dir):
            os.makedirs(file_dir)

        file_path = os.path.join( file_dir, f'{tile_y}.jpg' )
        # print(file_path)
        img.save(file_path)

    return img


def plain_PNG(file, image_size = 256 ):
    dataset = np.ndarray(shape=(image_size, image_size, 3), dtype=np.int8)
    try:
        image_data = ndimage.imread(file, mode='RGB').astype(int)
        dataset = image_data
        plain = False if 50135039-np.sum(dataset)>=0 else True     # 256*256*255*3 = 50135040
        return plain
    except:
        print('open images failed')


def tileXY_To_lnglat(tileX, tileY,ZOOM, in_sys = 'wgs', out_sys = 'wgs'):
    # 就算是Google地图，坐标也是GCJ02
    lng = tileX/pow(2,ZOOM)*360-180
    lat = math.atan( math.sinh( math.pi - 2*math.pi*( (tileY)/pow(2,ZOOM) ) ) )* 180/math.pi
    if in_sys == 'gcj' and out_sys == 'wgs':
        lng,lat = ct.gcj02_to_wgs84(lng,lat)
    return "%.7f, %.7f"%(lng,lat)
    # return lng,lat


def tileXYToLnglat(x, y, zoom):
    lng = x/math.pow(2,zoom)*360-180
    lat = math.atan(math.sinh(math.pi-2*math.pi*y/math.pow(2,zoom))) * 180 /math.pi
    return round(lng, 6), round(lat, 6)


def lnglatToTileXY(lng,lat,zoom):
    tileX = math.floor((lng+180)/360 * pow(2,zoom))
    tileY = math.floor( (0.5 -( math.log( math.tan( lat * math.pi / 180) + ( 1/math.cos( lat*math.pi /180)) , math.e) /2/math.pi) )* pow(2,zoom))
    return tileX, tileY


def image_compose(IMAGE_COLUMN, IMAGE_ROW, IMAGE_SIZE,save_image_or_not = True):
    if save_image_or_not:
        to_image = Image.new('RGB', (IMAGE_COLUMN * IMAGE_SIZE, IMAGE_ROW * IMAGE_SIZE)) #创建一个新图, for PNG mode = 'RGBA', JPG = "RGB"
    # 循环遍历，把每张图片按顺序粘贴到对应位置上
    for x in range( min_x, max_x + 1):
        for y in range( min_y, max_y+1 ):
            path = filePath+"/tile_"+ str(ZOOM)+"_" + str(x) + '_' + str(y)+".jpg"
            print(path)
            try:
                if save_image_or_not:
        
                    from_image = Image.open( path ).resize( (IMAGE_SIZE, IMAGE_SIZE), Image.ANTIALIAS)
                    to_image.paste( from_image, ((x - min_x ) * IMAGE_SIZE, (y - min_y) * IMAGE_SIZE) )
                # links
                linkInfo = '%d\t%d\t%d\t%s\t%d\t%d'%( (x-min_x)*IMAGE_COLUMN+(y-min_y), (x - min_x ) * IMAGE_SIZE, (min_y-y) * IMAGE_SIZE,  tileXY_To_lnglat( x, y ).replace(',',"\t"),x,y )
                # temp = str(x*IMAGE_COLUMN+y)+","+str((x - min_x ) * IMAGE_SIZE)+","+str((y - min_y) * IMAGE_SIZE) +","+ tileXY_To_lnglat( x, y )
                # print( linkInfo )
                links.write(linkInfo+"\n")
            except:
                print("数据缺失")
    return to_image.save(IMAGE_SAVE_PATH) # 保存新图


def writeLinks():
    
    pass


def merge_image(ZOOM = 18, PROJECTNAME = "福田核心区", filePath = 'D:/Tile', save_image_or_not = True, in_sys = 'wgs', out_sys = 'wgs'):
    IMAGE_SAVE_PATH = os.path.join( filePath, '../'+PROJECTNAME+'_'+str(ZOOM)+'.jpg') 
    LINKS_PATH = os.path.join( filePath, f'../links_{ZOOM}.txt')
    xs, ys = [], []

    links = open(LINKS_PATH, mode='w', encoding='utf-8')
    for parent,dirnames,filenames in os.walk(filePath):
        for filename in filenames:
            # print(filename)
            try:
                if int(str(filename).split("_")[1]) == ZOOM:
                    x = int(str(filename).split("_")[2])
                    y = int(str(filename).split("_")[3].split(".")[0])
                    if x not in xs:
                        xs.append(x)
                    if y not in ys:
                        ys.append(y)
            except:
                pass

    # 定义图像拼接函数
    IMAGE_SIZE = 256
    max_x, min_x, max_y, min_y = max(xs), min(xs), max(ys), min(ys)
    IMAGE_COLUMN = max_x - min_x + 1
    IMAGE_ROW    = max_y - min_y + 1
    print('%d, %d, %d, %d,(%d, %d)'% (max(xs), min(xs), max(ys), min(ys),IMAGE_COLUMN,IMAGE_ROW))

    # 以下为 原image_compose 代码
    if save_image_or_not:
        to_image = Image.new('RGB', (IMAGE_COLUMN * IMAGE_SIZE, IMAGE_ROW * IMAGE_SIZE)) #创建一个新图, for PNG mode = 'RGBA', JPG = "RGB"
    # 循环遍历，把每张图片按顺序粘贴到对应位置上
    for x in range( min_x, max_x + 1):
        for y in range( min_y, max_y+1 ):
            path = filePath+"/tile_"+ str(ZOOM)+"_" + str(x) + '_' + str(y)+".jpg"
            print(path)
            try:
                if save_image_or_not:
                    from_image = Image.open( path ).resize( (IMAGE_SIZE, IMAGE_SIZE), Image.ANTIALIAS)
                    to_image.paste( from_image, ((x - min_x ) * IMAGE_SIZE, (y - min_y) * IMAGE_SIZE) )
                # links
                # print((x-min_x)*IMAGE_COLUMN+(y-min_y), (x - min_x ) * IMAGE_SIZE, (min_y-y) * IMAGE_SIZE,  tileXY_To_lnglat( x, y,ZOOM, in_sys, out_sys ).replace(',',"\t"), x , y  )
                linkInfo = '%d\t%d\t%d\t%s\t%d\t%d'%( (x-min_x)*IMAGE_COLUMN+(y-min_y), (x - min_x ) * IMAGE_SIZE, (min_y-y) * IMAGE_SIZE,  
                                                       tileXY_To_lnglat(  x, y,ZOOM, in_sys, out_sys ).replace(',',"\t"),x,y )

                links.write(linkInfo+"\n")
            except:
                print("数据缺失")
                pass
    print( '%s, %s'%(tileXY_To_lnglat(  min_x, min_y, ZOOM, in_sys, out_sys ),  tileXY_To_lnglat(  max_x+1, max_y+1, ZOOM, in_sys, out_sys )))
    bbox = tileXY_To_lnglat(  min_x, min_y, ZOOM, in_sys, out_sys ).split(",") + tileXY_To_lnglat(  max_x+1, max_y+1, ZOOM, in_sys, out_sys ).split(',')
    links.close()
    return to_image.save(IMAGE_SAVE_PATH), [float(x) for x in bbox] # 保存新图


def merge_image_f_lst(f_lst, ZOOM, PROJECTNAME = "福田核心区", filePath = 'D:/Tile', save_image_or_not = True, in_sys = 'wgs', out_sys = 'wgs'):
    xs, ys = [], []

    for filename in f_lst:
        # print(filename)
        try:
            # if int(str(filename).split("_")[1]) == ZOOM:
            fn = str(filename).split("/")[-1].split("_")
            x = int(fn[2])
            y = int(fn[3].split(".")[0])
            if x not in xs:
                xs.append(x)
            if y not in ys:
                ys.append(y)
        except:
            pass

    # 定义图像拼接函数
    IMAGE_SIZE = 256
    max_x, min_x, max_y, min_y = max(xs), min(xs), max(ys), min(ys)
    IMAGE_COLUMN = max_x - min_x + 1
    IMAGE_ROW    = max_y - min_y + 1
    # print('%d, %d, %d, %d,(%d, %d)'% (max(xs), min(xs), max(ys), min(ys),IMAGE_COLUMN,IMAGE_ROW))

    # 以下为 原image_compose 代码
    if save_image_or_not:
        to_image = Image.new('RGB', (IMAGE_COLUMN * IMAGE_SIZE, IMAGE_ROW * IMAGE_SIZE)) #创建一个新图, for PNG mode = 'RGBA', JPG = "RGB"
    # 循环遍历，把每张图片按顺序粘贴到对应位置上
    postfix = '.jpg' if len( str(list(f_lst)[0]).split("/")[-1].split("_") ) <=4 else "_"+str(list(f_lst)[0]).split("/")[-1].split("_")[-1]
    # print( 'postfix: ', postfix )

    for x in range( min_x, max_x + 1):
        for y in range( min_y, max_y+1 ):
            path = filePath+"/tile_"+ str(ZOOM)+"_" + str(x) + '_' + str(y) + postfix
            # print(path)
            try:
                if save_image_or_not:
                    from_image = Image.open( path ).resize( (IMAGE_SIZE, IMAGE_SIZE), Image.ANTIALIAS)
                    to_image.paste( from_image, ((x - min_x ) * IMAGE_SIZE, (y - min_y) * IMAGE_SIZE) )
                linkInfo = '%d\t%d\t%d\t%s\t%d\t%d'%( (x-min_x)*IMAGE_COLUMN+(y-min_y), (x - min_x ) * IMAGE_SIZE, (min_y-y) * IMAGE_SIZE,  
                                                       tileXY_To_lnglat(  x, y,ZOOM, in_sys, out_sys ).replace(',',"\t"),x,y )

            except:
                # print("数据缺失")
                pass
    info = '%s, %s'%(tileXY_To_lnglat( min_x, min_y, ZOOM, in_sys, out_sys ),  tileXY_To_lnglat(  max_x+1, max_y+1, ZOOM, in_sys, out_sys ))
    bb = [float( x ) for x in info.split(',') ]
    # to_image.save(IMAGE_SAVE_PATH)
    return to_image, bb # 保存新图


if __name__ == "__main__":
    merge_image(ZOOM = 17, PROJECTNAME = "福田电子地图", filePath = 'D:/Tile', save_image_or_not = True, in_sys='gcj')
    # bbox, _ = merge_image(ZOOM = zoom, PROJECTNAME = "新洲路红荔路路口", filePath = root_path, save_image_or_not = True, in_sys = 'gcj', out_sys = 'wgs')
    pass

