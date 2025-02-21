import sys
from typing import Callable, Generic, TypeVar

from beancount.core import data
from beancount.parser import printer
from beangrow.investments import Cat

Memo = TypeVar("Memo")
Ret = TypeVar("Ret")
Directive = TypeVar("Directive", bound=data.Directive)  # type: ignore
Reducer = TypeVar("Reducer", bound=Callable[[Memo, Directive], Memo])


class TransactionProcessor(Generic[Memo, Ret, Directive]):
    """处理交易的处理器，可以注册多个 reducer 并对交易进行 reduce 操作"""

    def __init__(self):
        """初始化处理器"""
        self.registry: dict[str, tuple[Reducer, str]] = {}

    def register(
        self,
        categories_list: list[list[Cat]],
        description: str,
        func: Reducer,
    ):
        """注册一个处理特定类型交易的 reducer

        Args:
            categories_list: 多个交易类型列表
            description: reducer 的描述
            func: 处理函数
        """
        for categories in categories_list:
            key = "_".join(c.name for c in sorted(categories, key=lambda c: c.value))
            self.registry[key] = (func, description)

    def get_description(self, signature: str) -> str | None:
        """获取指定签名的 reducer 描述

        Args:
            signature: reducer 签名
        Returns:
            reducer 的描述，如果签名不存在则返回 None
        """
        _, description = self.registry.get(signature, (None, None))
        return description

    def reduce_transaction(self, memo: Memo, entry: Directive) -> Memo:
        """使用注册的 reducer 处理单个交易

        Args:
            memo: 当前的累积值
            entry: 要处理的交易
        Returns:
            处理后的新累积值
        """
        sig = entry.meta["signature"]
        try:
            handler, _ = self.registry[sig]
        except KeyError:
            epr = printer.EntryPrinter(stringify_invalid_types=True)
            print(epr(entry), file=sys.stderr)
            raise
        return handler(memo, entry)

    def reduce_transactions(
        self,
        init_value: Memo,
        entries: list[Directive],
        finalize: Callable[[Memo], Ret] | None = lambda x: x,
    ) -> Ret:
        """处理一批交易

        Args:
            entries: 要处理的交易列表
            init_value: reduce 操作的初始值
        Returns:
            所有交易处理完后的最终值
        """
        result = init_value
        for txn in entries:
            result = self.reduce_transaction(result, txn)

        return finalize(result)
