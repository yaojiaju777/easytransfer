"""planner/app_knowledge.py 的单元测试。"""

import pytest

from easytransfer.planner.app_knowledge import (
    APP_KNOWLEDGE_BASE,
    AppKnowledge,
    MigrationStrategy,
    get_all_known_apps,
    get_knowledge_count,
    lookup_app,
)


class TestKnowledgeBaseSize:
    """知识库规模测试。"""

    def test_has_at_least_50_entries(self):
        """知识库至少包含 50 个应用。"""
        assert get_knowledge_count() >= 50

    def test_get_all_returns_copy(self):
        """get_all_known_apps 返回副本，不影响原始数据。"""
        all_apps = get_all_known_apps()
        assert len(all_apps) == get_knowledge_count()
        # 修改副本不影响原始
        all_apps["test_key"] = AppKnowledge(display_name="Test")
        assert "test_key" not in APP_KNOWLEDGE_BASE


class TestLookupApp:
    """应用查找测试。"""

    def test_lookup_chrome(self):
        result = lookup_app("Google Chrome")
        assert result is not None
        assert result.display_name == "Google Chrome"
        assert result.winget_id == "Google.Chrome"

    def test_lookup_chrome_case_insensitive(self):
        result = lookup_app("google chrome")
        assert result is not None
        assert result.winget_id == "Google.Chrome"

    def test_lookup_vscode(self):
        result = lookup_app("Visual Studio Code")
        assert result is not None
        assert result.winget_id == "Microsoft.VisualStudioCode"

    def test_lookup_vscode_short_name(self):
        result = lookup_app("VS Code 1.87.0")
        assert result is not None
        assert result.winget_id == "Microsoft.VisualStudioCode"

    def test_lookup_git(self):
        result = lookup_app("Git")
        assert result is not None
        assert result.winget_id == "Git.Git"

    def test_lookup_7zip(self):
        result = lookup_app("7-Zip 24.01")
        assert result is not None
        assert result.winget_id == "7zip.7zip"

    def test_lookup_wechat(self):
        """中文应用名匹配。"""
        result = lookup_app("微信")
        assert result is not None
        assert "WeChat" in result.display_name

    def test_lookup_unknown_app(self):
        result = lookup_app("Some Completely Unknown App XYZ")
        assert result is None

    def test_lookup_firefox(self):
        result = lookup_app("Mozilla Firefox 120.0")
        assert result is not None
        assert result.winget_id == "Mozilla.Firefox"

    def test_lookup_python(self):
        result = lookup_app("Python 3.12.0")
        assert result is not None
        assert "Python" in result.winget_id

    def test_lookup_docker(self):
        result = lookup_app("Docker Desktop")
        assert result is not None
        assert result.winget_id == "Docker.DockerDesktop"

    def test_lookup_drawio(self):
        result = lookup_app("draw.io 29.6.1")
        assert result is not None


class TestAppKnowledgeContent:
    """知识库内容质量测试。"""

    def test_winget_apps_have_winget_id(self):
        """策略为 WINGET_INSTALL 的应用必须有 winget_id。"""
        for key, app in APP_KNOWLEDGE_BASE.items():
            if app.strategy == MigrationStrategy.WINGET_INSTALL:
                assert app.winget_id, f"{key} ({app.display_name}) 策略为 WINGET_INSTALL 但缺少 winget_id"

    def test_all_have_display_name(self):
        """所有条目都有显示名。"""
        for key, app in APP_KNOWLEDGE_BASE.items():
            assert app.display_name, f"{key} 缺少 display_name"

    def test_install_minutes_positive(self):
        """安装时间应为非负数。"""
        for key, app in APP_KNOWLEDGE_BASE.items():
            assert app.estimated_install_minutes >= 0, (
                f"{key} 的 estimated_install_minutes 为负: {app.estimated_install_minutes}"
            )

    def test_manual_apps_have_notes(self):
        """需要手动安装的应用应该有说明。"""
        for key, app in APP_KNOWLEDGE_BASE.items():
            if app.strategy == MigrationStrategy.MANUAL_DOWNLOAD:
                assert app.notes, f"{key} ({app.display_name}) 策略为 MANUAL_DOWNLOAD 但缺少 notes"

    def test_browsers_have_config_or_notes(self):
        """浏览器应该有配置路径或迁移说明。"""
        browser_keys = ["google_chrome", "mozilla_firefox", "microsoft_edge", "brave_browser"]
        for key in browser_keys:
            app = APP_KNOWLEDGE_BASE.get(key)
            assert app is not None, f"知识库缺少浏览器: {key}"
            assert app.config_paths or app.notes, f"{key} 缺少配置路径和说明"
