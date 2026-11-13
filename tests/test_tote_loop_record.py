import unittest

from nych_preview.tote_loop_record import REQUIRED_FIELDS, ToteLoopRecordError, require_tote_loop_fields


class ProvisionalToteLoopRecord(unittest.TestCase):
    def test_complete_record_is_accepted_without_a_type_check(self):
        require_tote_loop_fields(
            {
                "actor": 1,
                "action": "",
                "modality_operator": {"unspecified": True},
                "object": "present",
                "extra": "ignored",
            }
        )

    def test_each_missing_field_is_rejected(self):
        complete = {name: "present" for name in REQUIRED_FIELDS}
        for name in REQUIRED_FIELDS:
            record = dict(complete)
            del record[name]
            with self.subTest(missing=name):
                with self.assertRaises(ToteLoopRecordError) as raised:
                    require_tote_loop_fields(record)
                self.assertEqual(raised.exception.missing, (name,))
            record[name] = None
            with self.subTest(null=name):
                with self.assertRaises(ToteLoopRecordError) as raised:
                    require_tote_loop_fields(record)
                self.assertEqual(raised.exception.missing, (name,))

    def test_non_mapping_is_rejected(self):
        with self.assertRaises(TypeError):
            require_tote_loop_fields(["actor", "action", "modality_operator", "object"])


if __name__ == "__main__":
    unittest.main()
