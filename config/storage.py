"""
Where uploaded files are kept when SkillScope is deployed.

On a laptop, uploads go into the "media" folder next to manage.py. That does
not work on Render: its disk is wiped every time the app restarts or is
redeployed, so every uploaded video and PDF would silently disappear while
the database still pointed at it.

So when a CLOUDINARY_URL is configured, uploads go to Cloudinary instead.
settings.py switches to this storage automatically; with no CLOUDINARY_URL
nothing changes and files stay on disk.

Why this file exists instead of a ready-made package
----------------------------------------------------
Cloudinary files each have a "resource type" -- image, video or raw (anything
else, such as a PDF or a slide deck) -- and a file's address depends on it.
A single field here can hold a recorded lecture, a PowerPoint or a PDF, so the
type cannot be fixed per field. Uploading a PDF as an "image" simply fails.

This storage lets Cloudinary detect the type, then records it at the front of
the stored name, e.g.

    video/skillscope/resources/week1-lecture_ab12cd
    raw/skillscope/resources/notes_ef34gh.pdf
    image/skillscope/users/photos/me_ij56kl

so the right address can be rebuilt later from the name alone.
"""

import os
import urllib.request

import cloudinary
import cloudinary.uploader
import cloudinary.utils
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

# Everything SkillScope uploads is grouped under one folder in Cloudinary, so
# it is easy to find and cannot collide with anything else in the account.
ROOT_FOLDER = "skillscope"

RESOURCE_TYPES = ("image", "video", "raw")


class UploadFailed(Exception):
    """Cloudinary refused the file -- most often because it was too large."""


@deconstructible
class CloudinaryStorage(Storage):

    # -- saving --------------------------------------------------------------

    def _save(self, name, content):
        # "resources/week1.pdf" -> folder "skillscope/resources"
        folder, filename = os.path.split(name)

        # NOTE: new Cloudinary accounts refuse to deliver PDF and ZIP files
        # until "Allow delivery of PDF and ZIP files" is switched on under
        # Settings -> Security. Uploads still succeed, but every download
        # returns 401 -- so on a new account, switch that on before going live.

        if hasattr(content, "seek"):
            content.seek(0)

        try:
            result = cloudinary.uploader.upload(
                content,
                resource_type="auto",          # let Cloudinary decide
                folder=f"{ROOT_FOLDER}/{folder}".rstrip("/"),
                # Keep the original name but add a random suffix, so two
                # trainers each uploading "notes.pdf" get two separate files.
                # (Setting a fixed id instead would hand the second trainer
                # the FIRST trainer's file, silently.) Cloudinary also keeps
                # the extension for raw files and drops it for images and
                # video, which is exactly what their addresses need.
                use_filename=True,
                unique_filename=True,
                filename_override=filename,
            )
        except cloudinary.exceptions.Error as error:
            raise UploadFailed(str(error)) from error

        resource_type = result["resource_type"]
        public_id = result["public_id"]

        # Images and videos are addressed WITHOUT their extension (Cloudinary
        # stores the format separately); raw files keep it as part of their id.
        if resource_type != "raw" and result.get("format"):
            public_id = f"{public_id}.{result['format']}"

        return f"{resource_type}/{public_id}"

    def _open(self, name, mode="rb"):
        with urllib.request.urlopen(self.url(name), timeout=60) as response:
            return ContentFile(response.read(), name=name)

    # -- reading the stored name back ----------------------------------------

    @staticmethod
    def _split(name):
        """
        "video/skillscope/x.mp4" -> ("video", "skillscope/x.mp4")

        A name without a recognised prefix is treated as raw, so a file saved
        before this storage existed still produces a usable address.
        """
        resource_type, _, rest = name.partition("/")
        if resource_type in RESOURCE_TYPES and rest:
            return resource_type, rest
        return "raw", name

    def url(self, name):
        resource_type, public_id = self._split(name)
        url, _ = cloudinary.utils.cloudinary_url(
            public_id, resource_type=resource_type, secure=True)
        return url

    def delete(self, name):
        resource_type, public_id = self._split(name)
        if resource_type != "raw":
            public_id = os.path.splitext(public_id)[0]
        cloudinary.uploader.destroy(public_id, resource_type=resource_type)

    def exists(self, name):
        # Cloudinary adds its own unique suffix, so a clash is impossible.
        # Returning False stops Django renaming the file before upload.
        return False

    def size(self, name):
        return 0
