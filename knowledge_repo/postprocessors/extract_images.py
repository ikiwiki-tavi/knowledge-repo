import os
import re
import logging

from ..postprocessor import KnowledgePostProcessor

logger = logging.getLogger(__name__)


class ExtractImages(KnowledgePostProcessor):
    _registry_keys = ['extract_images']

    @classmethod
    def process(cls, kp):
        images = cls.find_images(kp.read())
        cls.collect_images(kp, images)
        cls.cleanup(kp)

    @classmethod
    def find_images(cls, md):
        images = []
        images.extend(cls.collect_images_for_pattern(
            md, '<img.*src=[\'"](.*?)[\'"].*>'))
        images.extend(cls.collect_images_for_pattern(md, '\!\[.*\]\((.*)\)'))
        return sorted(images, key=lambda x: x['offset'])

    @classmethod
    def collect_images_for_pattern(cls, md, pattern=None):
        p = re.compile(pattern)
        return [{'offset': m.start(), 'tag': m.group(0), 'src': m.group(1)} for m in p.finditer(md)]

    @classmethod
    def collect_images(cls, kp, images):
        if len(images) == 0:
            return
        md = kp.read()
        images = images[::-1]
        for image in images:
            if cls.skip_image(kp, image):
                continue
            orig_path = os.path.join(kp.orig_context, os.path.expanduser(image['src']))

            new_path = None
            if kp._has_ref(image['src']):
                new_path = cls.copy_image(kp, image['src'], is_ref=True)
            elif os.path.exists(orig_path):
                new_path = cls.copy_image(kp, orig_path)
            else:
                logger.warning("Could not find an image at: {}".format(image['src']))
            if not new_path:
                continue
            md = cls.replace_image_locations(md, image['offset'], image['tag'], image['src'], new_path)
        kp.write(md)

    @classmethod
    def skip_image(cls, kp, image):
        if re.match('http[s]?://', image['src']):
            return True
        if image['src'].startswith('images/') and image['src'] in kp.image_paths:
            return True
        return False

    @classmethod
    def copy_image(cls, kp, path, is_ref=False):
        if is_ref:
            return
        with open(path, 'rb') as f:
            kp.write_image(os.path.basename(path), f.read())
        return os.path.join('images', os.path.basename(path))

    @classmethod
    def replace_image_locations(cls, md, offset, match, old_path, new_path):
        pre = md[:offset]
        post = md[offset + len(match):]
        return pre + match.replace(old_path, new_path) + post

    @classmethod
    def cleanup(cls, kp):
        pass
