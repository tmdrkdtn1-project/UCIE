"""Offline Stage15 revision-window security and deterministic rotation tests."""
import unittest
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from ucie_miner.stage15_review_window import select_pending_public_revisions as select

class Stage15ReviewWindowTests(unittest.TestCase):
    def test_even_pending_rotation(self):
        leads=[("python/cpython",i,"a"*40,"b"*40) for i in range(4)]
        self.assertEqual([x[1] for x in select(leads,set(),limit=2,hour_index=0)],[0,1])
        self.assertEqual([x[1] for x in select(leads,set(),limit=2,hour_index=1)],[2,3])
        self.assertEqual([x[1] for x in select(leads,set(),limit=2,hour_index=2)],[0,1])

    def test_existing_revision_skipped_without_extra_reads(self):
        leads=[("python/cpython",i,"a"*40,"b"*40) for i in range(3)]
        prior={(leads[1][0],leads[1][1],leads[1][3])}
        self.assertEqual([x[1] for x in select(leads,prior,limit=2,hour_index=0)],[0,2])
        self.assertEqual(select(leads,set((x[0],x[1],x[3]) for x in leads),limit=2,hour_index=0),[])

    def test_invalid_budget_or_hour_fails_closed(self):
        for kwargs in ({"limit":0,"hour_index":0},
                       {"limit":3,"hour_index":0},
                       {"limit":True,"hour_index":0},
                       {"limit":1,"hour_index":-1},
                       {"limit":1,"hour_index":True}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                select([],set(),**kwargs)

if __name__=="__main__":
    unittest.main()
