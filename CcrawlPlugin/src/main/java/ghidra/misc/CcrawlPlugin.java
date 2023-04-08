@PluginInfo(
  status = PluginStatus.UNSTABLE,
  packageName = ExamplesPluginPackage.NAME,
  category = PluginCategoryNames.MISC,
  shortDescription = "Ccrawl interface",
  description = "Plugin providing a user interface "
              + "to ccrawl external tool and databsase. "
)

public class CcrawlPlugin extends ProgramPlugin {

    private CcrawlComponentProvider provider;

    public CcrawlPlugin(PluginTool tool) {
        super(tool, true, false);
        provider = new CcrawlComponentProvider(tool, getName());
    }

    @Override
    protected void programDactivated(Program program) {
        provider.clear();
    }

    @Override
    protected void locationChanged(ProgramLocation loc) {
        provider.locationChanged(currentProgram, loc);
    }
}


