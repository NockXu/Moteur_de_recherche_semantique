import unittest
from pathlib import Path
from common.Image_Classes.Image import Image, ProcessingStatus
from common.Dataset_Classes.Dataset import Dataset

class TestImage(unittest.TestCase):

    def setUp(self) -> None:
        self.dataset = Dataset(1, "test")
    
    def test_init(self):
        image_path = Path("test/test.jpg")
        image = Image(image_path, self.dataset)
        self.assertEqual(image.path, image_path)
        self.assertEqual(image.name, "test.jpg")
        self.assertEqual(image.status, ProcessingStatus.NOT_STARTED)
        self.assertEqual(image.dataset_id, self.dataset.id)
        self.assertEqual(image.dataset_name, self.dataset.name)
        self.assertIsNotNone(image.id)
        self.assertEqual(image.embedding, [])

        image2 = Image(path=image_path, dataset=self.dataset, image_id=1, name="test")
        self.assertEqual(image2.path, image_path)
        self.assertEqual(image2.name, "test")
        self.assertEqual(image2.status, ProcessingStatus.NOT_STARTED)
        self.assertEqual(image2.dataset_id, self.dataset.id)
        self.assertEqual(image2.dataset_name, self.dataset.name)
        self.assertEqual(image2.id, 1)
        self.assertEqual(image2.embedding, [])

    def test_to_dict(self):
        image_path = Path("test/test.jpg")
        image = Image(image_path, self.dataset)
        self.assertIsInstance(image.to_dict(), dict)

    def test_from_dict(self):
        image_path = Path("test/test.jpg")
        image = Image(image_path, self.dataset)
        dict_image = image.to_dict()
        image2 = Image.from_dict(dict_image)
        self.assertEqual(image2.path, image_path)
        self.assertEqual(image2.name, "test.jpg")
        self.assertEqual(image2.status, ProcessingStatus.NOT_STARTED)
        self.assertEqual(image2.dataset_id, self.dataset.id)
        self.assertEqual(image2.dataset_name, self.dataset.name)
        self.assertEqual(image2.id, image.id)
        self.assertEqual(image2.embedding, [])

    def test_status(self):
        image_path = Path("test/test.jpg")
        image = Image(image_path, self.dataset)
        self.assertEqual(image.status, ProcessingStatus.NOT_STARTED)
        
        self.assertFalse(image.is_processed)
        self.assertFalse(image.has_error)
        self.assertFalse(image.is_processing)

    def test_copy(self):
        image_path = Path("test/test.jpg")
        image = Image(image_path, self.dataset)
        image_copy = image.copy()
        self.assertEqual(image_copy.path, image.path)
        self.assertEqual(image_copy.name, image.name)
        self.assertEqual(image_copy.status, image.status)
        self.assertEqual(image_copy.dataset_id, image.dataset_id)
        self.assertEqual(image_copy.dataset_name, image.dataset_name)
        self.assertEqual(image_copy.id, image.id)
        self.assertEqual(image_copy.embedding, image.embedding)
        self.assertEqual(image_copy, image)
        
    def test_hash(self):
        image_path = Path("test/test.jpg")
        image = Image(image_path, self.dataset)
        self.assertEqual(hash(image), hash(image.id))
    
    def test_to_dict_dataset(self):
        dict_dataset = self.dataset.to_dict()
        self.assertIsInstance(dict_dataset, dict)