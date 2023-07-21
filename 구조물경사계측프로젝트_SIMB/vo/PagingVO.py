import math

class PagingVO:
    def __init__(self, total, nowPage, cntPerPage, cntPage):
        self.total = total
        self.nowPage = nowPage
        self.cntPerPage = cntPerPage
        self.cntPage = cntPage

        # 제일 마지막 페이지 계산
        self.lastPage = math.ceil(total / cntPerPage)

        # 시작, 끝 페이지 계산
        self.endPage = math.ceil(nowPage / cntPage) * cntPage
        if self.lastPage < self.endPage:
            self.endPage = self.lastPage
        self.startPage = math.floor((self.endPage - 1) / self.cntPage) * self.cntPage + 1
        if self.startPage < 1:
            self.startPage = 1

        # DB 쿼리에서 사용할 start, end값 계산
        self.end = self.nowPage * self.cntPerPage
        self.start = self.end - self.cntPerPage + 1