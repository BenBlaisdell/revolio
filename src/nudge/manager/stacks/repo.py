from revolio.manager.stack import ResourceGroup


class RepoResources(ResourceGroup):

    def __init__(self, config):
        super().__init__(config, prefix='Repo')
