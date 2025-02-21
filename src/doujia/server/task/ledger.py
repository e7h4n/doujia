import os

import git
from logzero import logger

from doujia.server.app import FlaskApp
from doujia.server.logic.ledger import load_beancount


def reload_ledger(app: FlaskApp) -> bool:
    """
    重新加载 beancount 文件
    当 git commit id 发生变化时才重新加载
    返回是否加载成功
    """
    ledger_path = os.path.join(app.ledger_root, "main.bean")
    logger.debug(f"Reloading ledger from {ledger_path}")

    # 获取 Git 仓库信息
    current_commit_id = None
    try:
        repo = git.Repo(app.ledger_root)
        current_commit_id = repo.head.commit.hexsha
    except git.InvalidGitRepositoryError:
        logger.warning(f"{app.ledger_root} is not a git repository")
    except Exception as e:
        logger.error(f"Failed to get git commit ID: {e!s}")

    # 如果 commit id 没有变化, 不需要重新加载
    if (
        hasattr(app, "ledger_commit_id")
        and current_commit_id is not None
        and app.ledger_commit_id == current_commit_id
    ):
        logger.debug("Ledger content not changed, skip reloading")
        return True

    logger.info(f"ledger commit ID changed: {current_commit_id}")

    # 更新 commit id 并重新加载
    app.ledger_commit_id = current_commit_id
    entries, doujia_config, options_map = load_beancount(ledger_path)

    app.entries = entries
    app.options_map = options_map
    app.doujia_config = doujia_config

    logger.info("Successfully reloaded beancount file")
    return True
