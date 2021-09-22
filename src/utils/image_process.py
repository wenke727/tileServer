import os
from PIL import Image
import matplotlib.pyplot as plt


def merge_tiles(f_lst, file_name_catalog=True):
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
            path = os.path.join(z_folder, f'{x}/{y}.jpg')
            try:
                from_image = Image.open( path ).resize( (IMAGE_SIZE, IMAGE_SIZE), Image.ANTIALIAS)
                to_image.paste( from_image, ((x - min_x ) * IMAGE_SIZE, (y - min_y) * IMAGE_SIZE) )
            except:
                print(f"数据缺失: {path}")
                pass

    return to_image



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

