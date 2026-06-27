import os

path = r'd:\ProjectRoot\PythonProject\ung_dung_hoc_tap\app\ui\widgets\quiz_widget.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add btn_test_all to UI
build_ui_find = '''        self.btn_toggle_list.clicked.connect(self._toggle_question_list)
        hdr.addWidget(self.btn_toggle_list)'''

build_ui_replace = '''        self.btn_toggle_list.clicked.connect(self._toggle_question_list)
        hdr.addWidget(self.btn_toggle_list)
        self.btn_test_all = QPushButton("📋 Test All")
        self.btn_test_all.setFixedHeight(30)
        self.btn_test_all.setToolTip("Test tất cả câu hỏi trong danh sách")
        self.btn_test_all.clicked.connect(self._start_test_all)
        hdr.addWidget(self.btn_test_all)'''

if build_ui_find in content:
    content = content.replace(build_ui_find, build_ui_replace)
else:
    print("Failed to patch _build_ui")

# 2. Add _start_test_all method
start_test_all_replace = '''    def _start_test_all(self):
        self._start_quiz(
            questions=self._all_questions,
            shuffle=False,
            update_source=True,
            mode="all",
        )

    def _refresh_list(self,'''

content = content.replace("    def _refresh_list(self,", start_test_all_replace)

# 3. Modify _refresh_list
refresh_list_find = '''    def _refresh_list(self, *_):
        session = get_session()
        try:
            q = session.query(CauHoi)
            cd, ch, bai = (
                self.topic_bar.get_chu_de_id(),
                self.topic_bar.get_chuong_id(),
                self.topic_bar.get_bai_id(),
            )
            if bai:
                q = q.filter(CauHoi.bai_id == bai)
            elif ch:
                ids = [b.id for b in session.query(Bai).filter(Bai.chuong_id == ch)]
                q = q.filter(CauHoi.bai_id.in_(ids))
            elif cd:
                cids = [c.id for c in session.query(Chuong).filter(Chuong.chu_de_id == cd)]
                bids = [b.id for b in session.query(Bai).filter(Bai.chuong_id.in_(cids))]
                q = q.filter(CauHoi.bai_id.in_(bids))
            questions = q.order_by(CauHoi.tao_luc).all()
            self._all_questions = [{
                "id": q.id, "noi_dung": q.noi_dung,
                "a": q.lua_chon_a, "b": q.lua_chon_b,
                "c": q.lua_chon_c, "d": q.lua_chon_d,
                "dap_an": q.dap_an, "giai_thich": q.giai_thich,
                "ghi_chu": q.ghi_chu,
            } for q in questions]
            self._test_questions = list(self._all_questions)
            self._questions = list(self._test_questions)
            self._quiz_mode = "all"
            self._random_test_size = None
            current_ids = {q["id"] for q in self._all_questions}
            self._question_results = {
                qid: result for qid, result in self._question_results.items()
                if qid in current_ids
            }
            if self._questions:
                self._q_index = 0
                self._rebuild_question_list(current_row=0)
                self._show_question(0)
            else:
                self._rebuild_question_list()
                self.lbl_question.setText("Chưa có câu hỏi nào")
                self.lbl_q_progress.setText("0 / 0")
                self.lbl_explain.hide()
                self.btn_explain.setEnabled(False)
                self.btn_explain.setText("➕ Giải thích")
            self._update_score_label()
        finally:
            session.close()'''

refresh_list_replace = '''    def _refresh_list(self, reset_test=True, *args):
        if not isinstance(reset_test, bool):
            reset_test = True
            
        session = get_session()
        try:
            q = session.query(CauHoi)
            cd, ch, bai = (
                self.topic_bar.get_chu_de_id(),
                self.topic_bar.get_chuong_id(),
                self.topic_bar.get_bai_id(),
            )
            if bai:
                q = q.filter(CauHoi.bai_id == bai)
            elif ch:
                ids = [b.id for b in session.query(Bai).filter(Bai.chuong_id == ch)]
                q = q.filter(CauHoi.bai_id.in_(ids))
            elif cd:
                cids = [c.id for c in session.query(Chuong).filter(Chuong.chu_de_id == cd)]
                bids = [b.id for b in session.query(Bai).filter(Bai.chuong_id.in_(cids))]
                q = q.filter(CauHoi.bai_id.in_(bids))
            questions = q.order_by(CauHoi.tao_luc).all()
            self._all_questions = [{
                "id": q.id, "noi_dung": q.noi_dung,
                "a": q.lua_chon_a, "b": q.lua_chon_b,
                "c": q.lua_chon_c, "d": q.lua_chon_d,
                "dap_an": q.dap_an, "giai_thich": q.giai_thich,
                "ghi_chu": q.ghi_chu,
            } for q in questions]
            
            if reset_test:
                self._test_questions = list(self._all_questions)
                self._questions = list(self._test_questions)
                self._quiz_mode = "all"
                self._random_test_size = None
                self._question_results.clear()
            else:
                new_all_dict = {q["id"]: q for q in self._all_questions}
                # Cập nhật self._questions giữ nguyên thứ tự
                new_questions = []
                for q in self._questions:
                    if q["id"] in new_all_dict:
                        new_questions.append(new_all_dict[q["id"]])
                # Thêm câu hỏi mới vào cuối
                existing_ids = {q["id"] for q in new_questions}
                for q in self._all_questions:
                    if q["id"] not in existing_ids:
                        new_questions.append(q)
                self._questions = new_questions
                
                new_test_questions = []
                for q in self._test_questions:
                    if q["id"] in new_all_dict:
                        new_test_questions.append(new_all_dict[q["id"]])
                existing_ids_test = {q["id"] for q in new_test_questions}
                for q in self._all_questions:
                    if q["id"] not in existing_ids_test:
                        new_test_questions.append(q)
                self._test_questions = new_test_questions
                
                current_ids = {q["id"] for q in self._all_questions}
                self._question_results = {
                    qid: result for qid, result in self._question_results.items()
                    if qid in current_ids
                }
                
            if self._questions:
                self._q_index = min(getattr(self, '_q_index', 0), len(self._questions) - 1)
                self._q_index = max(0, self._q_index)
                self._rebuild_question_list(current_row=self._q_index)
                self._show_question(self._q_index)
            else:
                self._rebuild_question_list()
                self.lbl_question.setText("Chưa có câu hỏi nào")
                self.lbl_q_progress.setText("0 / 0")
                self.lbl_explain.hide()
                self.btn_explain.setEnabled(False)
                self.btn_explain.setText("➕ Giải thích")
            self._update_score_label()
        finally:
            session.close()'''

if refresh_list_find in content:
    content = content.replace(refresh_list_find, refresh_list_replace)
else:
    print("Failed to patch _refresh_list")

# 4. Modify _shuffle_questions to clear results
shuffle_find = '''    def _shuffle_questions(self):
        if not self._questions:
            return
        random.shuffle(self._questions)
        self._q_index = 0'''

shuffle_replace = '''    def _shuffle_questions(self):
        if not self._questions:
            return
        random.shuffle(self._questions)
        self._question_results.clear()
        self._q_index = 0'''

if shuffle_find in content:
    content = content.replace(shuffle_find, shuffle_replace)
else:
    print("Failed to patch _shuffle_questions")

# 5. Modify edit/add/delete calls to self._refresh_list() -> self._refresh_list(reset_test=False)
content = content.replace("self._refresh_list()", "self._refresh_list(reset_test=False)")

# 6. Revert the topic_bar connection and __init__ call since they should reset the test
content = content.replace("self._refresh_list(reset_test=False)", "self._refresh_list()", 1) # first is in __init__
# We need to be careful. Let's just fix the topic_bar connection
content = content.replace("topic_bar.selection_changed.connect(self._refresh_list)", "topic_bar.selection_changed.connect(self._refresh_list)")
# The rest will be reset_test=False, which is fine for _add_q, _edit_q, _delete_q.

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Script execution completed")
