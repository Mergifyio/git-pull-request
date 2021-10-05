# Auto-Pull-Request

为了同步 github 库而生，为了自动化而生，为了解放 pull-request 繁琐而生

# Usages

- Fork: 在本地 clone 的 fork 库的改动上传到 github 并创建 pull-request
- Target: 在本地clone 的其他账户的原生target库上自动创建 fork，并推送内容到 fork 库，最后创建 pull-request
- None: 在本地非 clone 的local库 ，执行远程库，也会进行 fork、同步、pull-request
当然，在同步的过程中，会对 fork 库、target 库的被指定的分支进行rebase或者 base，支持checkout --ours/--theirs , 即覆盖另一个库的内容。
对 pull-request的文字内容进行了的 git log抽取，支持 vim 编辑，也直接跳过编辑。
# Pre-conditions
- Github fork账户的 [personal token](https://github.com/settings/tokens)，必须要有repo 权限

# Installation

```
pip install auto-pull-request
```

# Examples

Target:
```shell
apr --token $GITHUB_TOKEN  --fork-branch main --skip-editor --sync-merge --debug --quick-commit "ours"
```

Fork: 

```
apr --token $GITHUB_TOKEN --target-url $TARGET_URL --target-branch main --skip-editor --sync-merge --debug --quick-commit "ours"
```

None:

```
 apr --token $GITHUB_TOKEN --fork-url $FORK_URL --fork-branch main --target-url $TARGET-URL --target-branch main --skip-editor --debug 
```

# Why not

gh cli官方标配，但是不够自动化
Git-auto-request 不尽人意的内部代码，缺少一些人性化的优化。

