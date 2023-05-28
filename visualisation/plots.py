
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

green_paths = np.array([13.9, 5.6, 18.5])
full_network = np.array([9.4, 12.5, 22.0])

categories = ['Trees', 'Buildings', 'Total']

bar_width = 0.2
spacing = 0.05

bar_positions = [0, 1, 2]

# plot bars
plt.bar(bar_positions, green_paths, color='#00C642', width=bar_width, label='Green paths')
plt.bar([p + bar_width + spacing for p in bar_positions], full_network, color='grey', width=bar_width, label='Full network')

# plt.xlabel('Categories')
plt.ylabel('Shade coverage (%)')
# plt.title('Shade Coverage by Network')

plt.xticks([p + bar_width / 2 for p in bar_positions], categories)

fmt = '%.0f%%'
yticks = mtick.FormatStrFormatter(fmt)
plt.gca().yaxis.set_major_formatter(yticks)

fig_size = plt.gcf().get_size_inches()
new_height = fig_size[1] * 2/3
new_size = (fig_size[0], new_height)
plt.gcf().set_size_inches(new_size)

plt.tight_layout()
plt.legend()
plt.savefig('/Users/edibegovic/Desktop/chart.pdf')
plt.savefig('/Users/edibegovic/Dropbox/ITU/thesis/report/images/shade_bar_plot.pdf')
plt.show()
