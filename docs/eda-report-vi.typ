#set document(title: "Phân tích Khám phá Dữ liệu & Kết quả Ban đầu")
#set page(paper: "a4", margin: 2.4cm, numbering: "1")
#set text(size: 11pt, font: "New Computer Modern", lang: "vi")
#set par(justify: true)
#set heading(numbering: "1.1")
#set math.equation(numbering: "(1)")
#show link: underline

#let II(x) = $bold(1)[#x]$

#align(center)[
  #text(
    size: 17pt,
    weight: "bold",
  )[Phân tích Khám phá Dữ liệu & Kết quả Ban đầu] \
  #text(size: 13pt)[Yếu tố Đông đúc theo Tầng Ví (Tier-Aware Crowding) và \
    Cảnh báo sớm các Đợt Bùng phát Thanh lý Đồng bộ \
    trên Thị trường Hợp đồng Tương lai Vĩnh cửu On-chain] \
  #v(0.5em)
  #text(size: 11pt)[Luận văn Thạc sĩ Khoa học Máy tính] \
  #text(size: 11pt)[Tháng 7, 2026]
]

#v(1em)

#align(center)[#text(weight: "bold")[Tóm tắt]]
#block(inset: (x: 1.2em))[
  Báo cáo này phát triển và kiểm chứng độ khả thi cho một hướng nghiên cứu luận văn mới, dựa trên cơ sở dữ liệu `perpetuals_knowledge_graph` (40,5 triệu sự kiện log, 1,34 triệu vị thế đã đóng, 190.573 sự kiện thanh lý tường minh, 249 tài sản, 5 sàn giao dịch, 491 ngày dữ liệu). Chúng tôi dự báo các _đợt bùng phát thanh lý đồng bộ_ (synchronized liquidation bursts)---những khoảng thời gian ngắn trong đó nhiều vị thế hợp đồng tương lai vĩnh cửu (perpetual futures) trên cùng một tài sản bị đóng cưỡng bức cùng lúc---và đặt câu hỏi liệu các đặc trưng _đông đúc theo tầng ví_ (tier-aware crowding) có cải thiện khả năng dự báo so với mô hình nền tự kích thích (self-exciting) kiểu Hawkes hay không. Hai thử nghiệm khả thi được thực hiện trước khi xây dựng bất kỳ mô hình nào. (i) Giả thuyết _"nam châm thanh lý"_ (giá bị hút về các vùng giá thanh lý dày đặc) đã bị *bác bỏ* trên ba tài sản thanh khoản cao nhất, dưới hai dạng kiểm định độc lập (đều cho kết quả null). (ii) Nhãn _bùng phát thanh lý_ (burst) đã *vượt qua thử nghiệm một cách thuyết phục*: nhãn này dày đặc và có khả năng học mạnh---chỉ một đặc trưng cường độ trễ (trailing-intensity) đơn lẻ đã đạt AUC 0,83--0,87, xác nhận hiện tượng tự kích thích. Trên một phép chia dữ liệu theo thời gian, an toàn không rò rỉ (4,2 triệu dòng tài sản-khung giờ, 40 tài sản), một mô hình gradient boosting được tinh chỉnh với đặc trưng đông đúc (mất cân bằng theo tầng, lan tỏa liên tài sản, giá trị danh nghĩa thanh lý; 17 đặc trưng) được so sánh với ba mô hình nền _có tên gọi, đã công bố_, cùng huấn luyện trên dữ liệu giống nhau: một quá trình Hawkes đơn biến cổ điển (ước lượng hợp lý cực đại), một Hawkes đa biến có thành phần thị trường, và một Transformer Hawkes Process thần kinh @zuo2020thp. Sau đó, ba mô hình sử dụng đặc trưng hiệp biến (covariate) được đánh giá: bộ phân loại đã tinh chỉnh, một quá trình điểm thần kinh (neural point process) có điều kiện hiệp biến (mô hình hazard dựa trên GRU trên chuỗi đặc trưng), và một mạng nơ-ron đồ thị không gian--thời gian (spatio-temporal GNN) trên đồ thị liên tài sản. Trên độ đo precision-recall---thước đo trung thực cho một tập kiểm tra có tỷ lệ dương chỉ 0,56%---cả ba mô hình đều vượt trội hơn cả ba mô hình nền với khoảng cách lớn; quá trình điểm có điều kiện hiệp biến (CovTPP) đạt kết quả tốt nhất (PR-AUC 0,256, so với 0,157 của Hawkes cổ điển và 0,129 của THP thần kinh, mức tăng từ +0,10 đến +0,13), nhỉnh hơn một chút so với GNN (0,251) và bộ phân loại đã tinh chỉnh (0,250). Yếu tố quyết định chính là các đặc trưng hiệp biến, được chứng minh _trong cùng một họ mô hình_: quá trình điểm thần kinh gần như _tăng gấp đôi_ PR-AUC (0,129→0,256) khi được điều kiện hóa theo đặc trưng đông đúc thay vì chỉ dựa vào thời điểm sự kiện. Đáng chú ý, tất cả các mô hình nền chỉ dựa vào cường độ (intensity-only) đều đạt ROC-AUC ≈0,97 nhưng PR-AUC chỉ ≈0,13--0,16: cường độ tự kích thích là một bộ xếp hạng (ranker) mạnh nhưng là tín hiệu độ chính xác (precision) yếu dưới điều kiện mất cân bằng---điều mà ROC che giấu còn PR-AUC phơi bày. Khác với công thức chấm điểm kỹ năng ví (wallet-scoring) trước đây---nơi nhãn đánh giá gần như 99% là nhiễu lấy mẫu---bài toán này có một nhãn dày đặc, đáng tin cậy, nên mức cải thiện đo được là có ý nghĩa thực chất. Một walk-forward xoay vòng năm fold xác nhận mức tăng đông đúc của LightGBM không phải hiện tượng giả tạo của một phép chia đơn (mức tăng PR-AUC +0,024 ± 0,013, mức tăng ROC-AUC +0,054 ± 0,017, dương ở mọi fold), và giữ vững qua các chế độ tăng/giảm giá, biến động cao/thấp, và đông đúc cao/thấp---lớn nhất chính xác ở giai đoạn căng thẳng và đông đúc thấp, nơi mô hình nền tự kích thích yếu nhất.
]

#v(1em)

= Bối cảnh Thể chế (Institutional Background) <sec:institutional>

Phần này giải thích các khái niệm thị trường được dùng xuyên suốt báo cáo, để người đọc không chuyên về thị trường phái sinh crypto vẫn theo dõi được các phần sau.

== Hợp đồng tương lai vĩnh cửu (Perpetual Futures) là gì

Hợp đồng tương lai vĩnh cửu (perpetual futures, viết tắt perp) là một công cụ phái sinh cho phép giao dịch có đòn bẩy trên giá của một tài sản (ví dụ BTC, SOL) mà không có ngày đáo hạn, khác với hợp đồng tương lai truyền thống. Vì không có ngày đáo hạn để giá hợp đồng tự động hội tụ về giá giao dịch spot, cơ chế giữ cho giá perp bám sát giá spot là tỷ lệ tài trợ (funding rate): định kỳ (thường mỗi 1–8 giờ), bên nắm giữ vị thế mua (long) và bên nắm giữ vị thế bán (short) thanh toán một khoản phí nhỏ cho nhau, tỷ lệ thuận với chênh lệch giữa giá perp và giá chỉ số (index/oracle price). Khi giá perp cao hơn giá spot, long trả phí cho short (khuyến khích bán, kéo giá xuống); khi thấp hơn sẽ theo chiều ngược lại. Perp hiện là công cụ phái sinh crypto phổ biến nhất và ngày càng đóng vai trò trung tâm trong việc khám phá giá.



== Đòn bẩy, Ký quỹ và Cơ chế Thanh lý (Liquidation)

Một vị thế perp được mở bằng một khoản ký quỹ ban đầu (initial margin) m, nhân với đòn bẩy (leverage) ℓ để có quy mô vị thế danh nghĩa s = m × ℓ (ví dụ: ký quỹ 100 USD, đòn bẩy 10x => vị thế trị giá 1000 USD). Sàn/giao thức yêu cầu vị thế luôn duy trì một mức ký quỹ duy trì (maintenance margin) tối thiểu, tính theo tỷ lệ ký quỹ hiện tại trên quy mô vị thế. Khi giá thị trường di chuyển ngược hướng vị thế đủ để tỷ lệ ký quỹ giảm xuống dưới ngưỡng duy trì, vị thế đó chạm giá thanh lý (liquidation price) - xấp xỉ


$
  P_"liq" approx P_"entry" times (1 minus.plus 1/ell) quad ("Long: " -,quad "Short: " +),
$
và bị *đóng cưỡng bức* (force-closed), có nghĩa là sàn hoặc giao thức (hoặc một _keeper_/liquidator bên thứ ba được thưởng phí) tự động đóng vị thế bằng cách khớp một lệnh ngược chiều ra thị trường, bất kể chủ vị thế có đồng ý hay không. Đòn bẩy càng cao, khoảng cách tới giá thanh lý càng hẹp.


== Cơ chế gây ra Đợt Bùng phát Thanh lý (Liquidation Cascade)

Rủi ro hệ thống đặc trưng của perp là *thanh lý dây chuyền* (liquidation cascade): việc đóng cưỡng bức một vị thế long tạo ra một lệnh *bán* ra thị trường; việc đóng một vị thế short tạo ra một lệnh *mua*. Nếu nhiều vị thế cùng chiều tập trung quanh một vùng giá thanh lý gần nhau (tức là vị thế nằm quanh một chiều và tập trung), việc thanh lý loạt vị thế đầu tiên đẩy giá đi xa hơn theo đúng hướng đã gây thanh lý, kích hoạt lớp vị thế đòn bẩy tiếp theo chạm ngưỡng thanh lý của chính nó - một chuỗi phản ứng tự kích thích, lây lan (self-exciting, contagious).


== Hai kiến trúc perp on-chain: Hyperliquid và Jupiter

Dữ liệu của luận văn trải trên 5 sàn/giao thức, nhưng hai kiến trúc đối lập đáng chú ý nhất---và là nguồn dữ liệu giá chính (`hyperliquid_prices`)---là:

- *Hyperliquid*: một sàn perp phi tập trung vận hành trên một blockchain Lớp-1 (L1) riêng do chính Hyperliquid xây dựng, sử dụng cơ chế đồng thuận HyperBFT với thời gian tạo khối dưới một giây. Khớp lệnh theo mô hình *sổ lệnh giới hạn trung tâm on-chain* (on-chain central limit order book, CLOB)---tương tự sàn tập trung (CEX) truyền thống nhưng toàn bộ sổ lệnh và khớp lệnh đều diễn ra on-chain. Một _vault_ nội bộ (HLP) đóng vai trò nhà tạo lập thị trường và hấp thụ một phần rủi ro thanh lý khi thanh khoản sổ lệnh không đủ.
- *Jupiter Perpetuals* (trên Solana): không dùng sổ lệnh, mà dùng mô hình *giao dịch đối ứng với hồ thanh khoản* (pool-based/peer-to-pool): mọi trader giao dịch trực tiếp với một hồ thanh khoản chung (JLP pool), hồ này đóng vai trò đối tác cho mọi vị thế và gánh lãi/lỗ ròng của toàn bộ trader. Giá tham chiếu để định giá vị thế và xác định thời điểm thanh lý lấy từ *oracle* giá bên ngoài (ví dụ Pyth Network) thay vì từ khớp lệnh nội bộ.

Sự khác biệt kiến trúc này (sổ lệnh vs. hồ thanh khoản, cơ chế giá nội sinh vs. oracle) là lý do báo cáo không giả định một cơ chế thanh lý thống nhất duy nhất, mà xây dựng nhãn bùng phát @eq:burst và các đặc trưng đông đúc (@sec:formulation) một cách _bất khả tri với sàn_ (venue-agnostic), gộp sự kiện thanh lý từ `close_action = Liquidate` trên toàn bộ 5 sàn/chuỗi, đồng thời giữ venue như một _mark_ tùy chọn trong công thức cường độ đa biến (@eq:intensity).

== Đầu ra của mô hình: hệ thống dự đoán điều gì

Với mỗi tài sản $a$ và mỗi khung 5 phút $t$, hệ thống dự đoán một *xác suất nhị phân*: liệu trong cửa sổ $h$ phút tiếp theo, số lượng sự kiện thanh lý trên tài sản $a$ có đạt hoặc vượt ngưỡng $theta$ hay không (định nghĩa hình thức tại @eq:burst, @sec:formulation). Đây *không phải* là dự đoán chiều giá (tăng/giảm), cũng không phải dự đoán một sự kiện thanh lý đơn lẻ, mà là dự đoán _cụm sự kiện đồng bộ_---một tín hiệu cảnh báo sớm rủi ro thác thanh lý, hướng tới ứng dụng thực tế: cảnh báo cho nhà quản lý rủi ro hoặc chính trader trước khi một đợt bùng phát xảy ra.


== Quá trình Hawkes

Quá trình Hawkes là một quá trình điểm ngẫu nhiên (_self-exciting point process_) mà trong đó sự xuất hiện của một sự kiện làm tăng xác suất xuất hiện các sự kiện tiếp theo trong một khoảng thời gian ngắn. Một quá trình Hawkes đơn biến mô hình hóa cường độ điều kiện của các sự kiện thanh lý dưới dạng một tỷ lệ nền hằng số $mu$ cộng tổng các kích thích suy giảm do mỗi sự kiện quá khứ đóng góp: $ lambda(t) = mu + sum_{t_j<t} alpha e^{-beta(t-t_j)} $.
với:
- $lambda(t)$: *cường độ có điều kiện* tại thời điểm $t$, biểu diễn tốc độ kỳ vọng xuất hiện sự kiện ngay tại thời điểm đó, với điều kiện đã biết toàn bộ lịch sử trước $t$. Giá trị $lambda(t)$ càng lớn thì khả năng xảy ra sự kiện trong khoảng thời gian rất ngắn tiếp theo càng cao.
- $mu$: *cường độ nền (baseline intensity)*, là tốc độ xảy ra sự kiện khi không chịu ảnh hưởng từ các sự kiện trước đó.
- $sum_{t_j<t}$: tổng trên tất cả các sự kiện đã xảy ra trước thời điểm ttt.
- $alpha$: *hằng số tính độ mạnh của hiệu ứng kích thích*. Mỗi khi một sự kiện xảy ra, cường độ sẽ tăng thêm một lượng ban đầu bằng $alpha$.
  - $alpha$ lớn → mỗi sự kiện tạo ảnh hưởng mạnh.
  - $alpha$ nhỏ → ảnh hưởng yếu.
- $e^{-beta(t-t_j)}$: *hàm suy giảm theo thời gian*.
  - $t-t_j$: khoảng thời gian kể từ khi sự kiện j xảy ra.
  - $beta$: hằng số tốc độ suy giảm.
    - $beta$ lớn → ảnh hưởng mất đi rất nhanh.
    - $beta$ nhỏ → ảnh hưởng kéo dài.


Mỗi sự kiện $j$ nâng cường độ lên ngay lập tức một lượng $alpha$, sau đó suy giảm theo hàm mũ với tốc độ $beta$ về lại $mu$; khi nhiều sự kiện xảy ra gần nhau, các mức kích thích cộng dồn khiến cường độ tăng vọt hẳn lên, vượt quá threshold - đây chính xác là hình ảnh của một thác thanh lý ở cấp độ đếm sự kiện. @fig:hawkesexample mô phỏng một quá trình ổn định (dưới ngưỡng tới hạn), tỷ lệ phân nhánh 𝛼 𝛽 ≈ 0, 61 < 1, và vẽ đường cường độ cùng với các thời điểm sự kiện mô phỏng: giai đoạn yên tĩnh nằm ở mức 𝜇. Mỗi một sự kiện xảy ra sẽ tạo ra một bước nhảy rõ rệt rồi suy giảm, với một cụm ba sự kiện gần nhau đẩy 𝜆(𝑡) lên gần gấp 5 lần mức nền trước khi hạ nhiệt.


#figure(
  image("figs_vi/hawkes_example.pdf", width: 92%),
  caption: [Ví dụ minh họa đường cường độ Hawkes tự kích thích (mô phỏng; $mu=0,3$, $alpha=0,55$, $beta=0,9$, tỷ lệ phân nhánh $alpha/beta approx 0,61$). Các vạch đứng là thời điểm sự kiện mô phỏng; đường cong là $lambda(t)$. Mỗi sự kiện kích hoạt một bước nhảy tức thời độ lớn $alpha$ rồi suy giảm mũ với tốc độ $beta$; một cụm sự kiện gần nhau cộng dồn các bước nhảy này thành một đợt bùng phát rõ rệt trước khi $lambda(t)$ hạ về lại mức nền $mu$ (nét đứt).],
) <fig:hawkesexample>

= Phát biểu Bài toán <sec:formulation>

== Vì sao Dự báo Đợt Bùng phát Thanh lý lại quan trọng

Hợp đồng tương lai vĩnh cửu là công cụ phái sinh crypto phổ biến nhất. Rủi ro hệ thống đặc trưng của chúng là thanh lý dây chuyền: khi một cụm vị thế đòn bẩy vi phạm ngưỡng ký quỹ duy trì, các lệnh thanh lý cưỡng bức sẽ được bán ra thị trường, đẩy giá trên hợp đồng tương lai đi xa hơn, và kích hoạt lớp vị thế đòn bẩy tiếp theo — một chuỗi tháo chạy tự kích thích, lây lan. Các tín hiệu cảnh báo sớm hiện có mà giới thực hành sử dụng (tỷ lệ tài trợ cực đoan, mất cân bằng long/short, open interest kỷ lục) là các ngưỡng heuristic, không phải mô hình dự báo đã hiệu chỉnh. Chính vì vậy nghiên cứu đặt ra một câu hỏi quan trọng hơn, có thể học được: _cho trạng thái thị trường tại thời điểm $t$, xác suất xảy ra một đợt bùng phát thanh lý đồng bộ trong $h$ phút tiếp theo là bao nhiêu, và các đặc trưng đông đúc phân giải theo tầng ví có cải thiện dự báo đó so với một mô hình nền thuần túy tự kích thích hay không_?

== Giả thuyết Đông đúc (Crowding Hypothesis)
Hiện tượng "đông đúc" (crowding) trong trường hợp này tức là khi mức độ các vị thế trong một tầng ví (wallet tier) - ví dụ như ví lớn, ví nhỏ - cùng tập trung vào một hướng bên trong giao dịch, và tương đương cùng một mức đòn bẩy, thì chỉ cần một biến động giá nhỏ cũng đủ để kích hoạt thanh lý hàng loạt, vì nhiều ví cùng chạm đến một ngưỡng thanh lý đồng thời.

== Định nghĩa Hình thức của Đợt Bùng phát

Gọi $L_(a,t)$ là số sự kiện thanh lý của tài sản $a$ trong khung 5 phút $t$. Nhãn bùng phát tại tầm dự báo $h$ (tính theo số khung) và ngưỡng $theta$ là
$ Y_(a,t)^((h)) = II(sum_(tau in (t,\, t+h]) L_(a,tau) gt.eq theta) $ <eq:burst>
Nhãn chỉ sử dụng cửa sổ _tương lai_ $(t, t+h]$; mọi biến dự báo được tính trên cửa sổ _quá khứ_ $[t-w, t]$, do đó đặc trưng và nhãn tách biệt nhau theo cấu trúc. @sec:m0burst cố định điểm vận hành tại $h=3$ khung (15 phút), $theta=3$.

== Phân rã Cường độ Bùng phát

Chúng tôi mô hình hóa cường độ điều kiện của các sự kiện thanh lý cho tài sản $a$ (và, trong mô hình đầy đủ, các _mark_ tầng ví và sàn giao dịch $k$) như một quá trình tự kích thích với một hàm nền điều kiện hóa theo hiệp biến:
$
  lambda_k (t) = underbrace(mu_k (x_k (t)), "hàm nền điều kiện hóa theo đông đúc") + sum_(k') sum_(t_j < t) alpha_(k'->k) phi(t - t_j)
$ <eq:intensity>
trong đó
- $K = {1,dots,K}$: tập các mark (cặp ví-tầng-sàn);
- $x_k(t) in R^p$: véc-tơ hiệp biến đông đúc tại mark $k$, quan sát được tại thời điểm $t^-$;
- $mu_k: R^p -> R_{>0}$: hàm nền điều kiện hóa theo đông đúc, ví dụ $mu_k(x) = exp(beta_k^top x)$;
- $t_j^{k'}$: thời điểm sự kiện thanh lý thứ $j$ trên mark $k'$, trước $t$;
- $phi_{k' -> k}(dot)$: hạt nhân kích hoạt từ mark $k'$ sang mark $k$, dạng mũ $phi_{k'\to k}(u) = beta_{k'\to k}\, e^{-beta_{k'\to k} u}$ với $u>0$;
- $alpha_{k'\to k} gt.eq 0$: cường độ lây lan chéo-mark (chéo-tầng, chéo-sàn) từ $k'$ sang $k$.

Giả thuyết trung tâm của luận văn là $x_k(t)$ sẽ mang thông tin
về các đợt bùng phát tương lai vượt ra ngoài những gì lịch sử sự kiện gần đây có thể cung cấp.

@fig:intensity cho thấy ánh xạ vào hai số hạng của @eq:intensity.

#figure(
  image("figs_vi/intensity.pdf", width: 90%),
  caption: [Phân rã cường độ bùng phát, @eq:intensity. Các mô hình nền đã công bố chỉ mô hình hóa số hạng tự kích thích (phải); các mô hình sử dụng hiệp biến trong luận văn này cung cấp hàm nền điều kiện hóa theo đông đúc (trái). Luận văn đo _mức tăng_ khi bổ sung số hạng bên trái, được tách bạch rõ nhất trong họ TPP thần kinh (THP → CovTPP).],
) <fig:intensity>

== Giả thuyết Đông đúc (Crowding Hypothesis)
Hiện tượng "đông đúc" (crowding) trong trường hợp này tức là khi mức độ các vị thế trong một tầng ví (wallet tier) - ví dụ như ví lớn, ví nhỏ - cùng tập trung vào một hướng bên trong giao dịch, và tương đương cùng một mức đòn bẩy, thì chỉ cần một biến động giá nhỏ cũng đủ để kích hoạt thanh lý hàng loạt, vì nhiều ví cùng chạm đến một ngưỡng thanh lý đồng thời.


Đông đúc làm mỏng "biên độ an toàn" của thị trường: khi vị thế tập trung và lệch một chiều---đặc biệt ở các ví lớn---một biến động bất lợi vừa phải cũng đủ thanh lý nhiều vị thế cùng lúc. Do đó, với mỗi tài sản và mỗi khung 5 phút, chúng tôi xây dựng các đặc trưng mà một đại lượng vô hướng đơn lẻ như tỷ lệ tài trợ không thể biểu đạt được: mất cân bằng long/short theo open interest, mất cân bằng theo từng tầng (ví nhỏ/trung/lớn), độ bất đồng nhỏ-so-với-lớn, mức độ tập trung vị thế, đòn bẩy trung bình của các vị thế đang mở, và tốc độ biến thiên của các đại lượng này. Mục tiêu dự đoán @eq:burst kiểm định trực tiếp liệu các hiệp biến này có làm tăng xác suất bùng phát hay không.


== Đóng góp

Tóm gọn trong một câu: _Khi thêm một hiệp biến biểu thị cho sự đông đúc vào trong hàm nền cường độ của một quá trình tự kích thích, tăng gấp đôi PR-AUC so với các mô hình nền quá trình điểm chỉ dựa vào cường độ, trên một dự báo bùng phát thanh lý ngoài mẫu, an toàn không rò rỉ._ Cụ thể:

- *(C1)* Một bảng đông đúc phân giải theo tầng ví và nhãn bùng phát an toàn không rò rỉ, xây dựng từ 40,5 triệu sự kiện on-chain thô (4,24 triệu dòng tài sản-khung, 40 tài sản; @sec:system to @sec:m0burst), với hai thử nghiệm khả thi được chạy _trước khi_ mô hình hóa để giảm rủi ro hướng đi.
- *(C2)* Một quá trình điểm thần kinh điều kiện hóa theo hiệp biến (CovTPP) hiện thực hóa hàm nền điều kiện hóa theo đông đúc $mu_k (dot)$ của @eq:intensity, tách bạch hiệu ứng hiệp biến _trong cùng_ họ TPP thần kinh, đối chứng với mô hình nền Transformer Hawkes Process.
- *(C3)* Các đặc trưng lan tỏa liên tài sản tường minh và một GNN không gian--thời gian trên đồ thị vị thế, đối chứng với một quá trình Hawkes đa biến có thành phần thị trường.
- *(C4)* Một đánh giá ưu tiên precision-recall trên các khung kiểm tra ngoài mẫu giống hệt nhau, qua sáu mô hình có tên gọi (@sec:results), phơi bày một sự phân kỳ ROC/PR mà báo cáo chỉ dựa vào ROC sẽ che giấu.

@sec:gap định vị mỗi đóng góp đối chứng với một khoảng trống cụ thể, có trích dẫn, trong các công trình trước đây.

= Công trình Liên quan (Related Work) <sec:related>

Chúng tôi tổ chức các công trình liên quan theo năm hướng nghiên cứu mà luận văn này nằm ở giao điểm, và nêu rõ tại @sec:gap chính xác vị trí mỗi hướng còn thiếu so với một dự báo bùng phát thanh lý có hiệu chỉnh, nhận biết đông đúc.

*Quá trình tự kích thích sinh ra thanh lý dây chuyền.* Mô hình hóa các sự kiện tài chính tập trung thành cụm như quá trình tự kích thích (Hawkes) đã được thiết lập vững chắc: @bacry2015hawkes khảo sát quá trình Hawkes trong tài chính, và @hardiman2013endogeneity dùng tỷ lệ phân nhánh (branching ratio) để định lượng tính nội sinh/phản xạ của thị trường (endogeneity/reflexivity)---cùng cơ chế mà @filimonov2012reflexivity gắn với các đợt sụp đổ chớp nhoáng (flash crash). Công trình DeFi gần nhất, @cao2025defi, cho thấy các sự kiện thanh lý tập trung thành cụm ảnh hưởng đến nhiều giao thức trong một khung Hawkes đa biến, còn @markovhawkes2025manipulation mở rộng cường độ Hawkes với một hàm nền điều biến kiểu Markov để phát hiện thao túng thị trường. Toàn bộ các hướng này mô hình hóa cường độ chỉ từ _lịch sử sự kiện_ (@eq:intensity, số hạng thứ hai); trạng thái vị thế/đông đúc không bao giờ đi vào hàm nền $mu_k$. Một hướng nowcasting song song @nowcast2023crashrisk dự đoán rủi ro sụp đổ từ mất cân bằng dòng lệnh (order-flow imbalance) nhưng không dựa trên vị thế phân giải theo tầng ví.

*Cấu trúc thị trường perpetual và rủi ro thanh khoản.* Rủi ro thanh khoản hướng tới tương lai cho perp bắt đầu thu hút các khung phân tích chuyên biệt như Slippage-at-Risk @slippageatrisk2026, định lượng rủi ro thực thi lệnh nhưng coi thanh lý là một cú sốc thanh khoản ngoại sinh, chứ không phải một luồng sự kiện tự kích thích, dự báo được.

*Quá trình điểm thời gian có đánh dấu sử dụng mạng neuron (Neural Marked Temporal Point Process).* Một họ mô hình phong phú điều kiện hóa cường độ sự kiện theo lịch sử đã học: quá trình điểm thời gian có đánh dấu hồi quy @du2016rmtpp, quá trình Hawkes sử dụng mạng neuron @mei2017neuralhawkes, Transformer Hawkes Process @zuo2020thp, quá trình mạng neuron không gian--thời gian @zhou2022neuralstpp, dự báo đa sự kiện không gian--thời gian @beyondhawkes2022, và các biến thể state-space gần đây @mambahawkes2024, được so sánh bởi benchmark EasyTPP @xue2023easytpp. Các phương pháp này điều kiện hóa theo thời điểm sự kiện và đánh dấu phân loại, nhưng---như mô hình nền THP của chúng tôi cho thấy bằng thực nghiệm---không điều kiện hóa theo các hiệp biến đông đúc liên tục, ngoại sinh; độ chính xác cao hơn so với mô hình Hawkes cổ điển nhưng vẫn có độ chính xác tương đương khi chỉ được cấp thời điểm sự kiện (@tab:m2).

*Cấu trúc tô-pô và liên tài sản của đồ thị on-chain.* Cấu trúc mạng blockchain mang tín hiệu cảnh báo sớm: phát hiện bất thường tô-pô trên mạng đa lớp động @oforiboateng2021topological, đặc trưng tô-pô cho dự đoán bất thường giá @xrp2026topological, và phát hiện bất thường mạng theo tốc độ bền vững (persistence velocity) @persistencevelocity2025. Những công trình này là động lực cho đồ thị liên tài sản của chúng tôi (ST-GNN, @sec:results) nhưng nhắm tới bất thường giá/nhãn trên đồ thị giao dịch, không phải các đợt bùng phát thanh lý đồng bộ trên một đồ thị vị thế liên tài sản.

*Dự đoán conformal dưới dịch chuyển phân phối.* Vì tần suất bùng phát bị dịch chuyển (tỷ lệ nền tập kiểm tra 0,56% so với tập huấn luyện 1,51%, @sec:results), độ bất định đã hiệu chỉnh phải sống sót qua tính phi dừng: suy luận conformal thích nghi @gibbs2021adaptive, dự đoán conformal cho chuỗi thời gian @zaffran2022adaptive, và luồng conformal nhận biết dịch chuyển @driftconformal2026. Các công trình này cung cấp tầng hiệu chỉnh cho hệ thống được hoạch định nhưng chưa từng được áp dụng cho một quá trình điểm bùng phát thanh lý.

= Khoảng trống Nghiên cứu và Đóng góp <sec:gap>

Đọc năm hướng nghiên cứu cùng nhau, ta thấy một giao điểm cụ thể còn bỏ trống.

*G1 --- Các mô hình dựa trên thanh lý hàng loạt chỉ dựa vào cường độ bỏ qua đông đúc.* Các mô hình thanh lý DeFi/tài chính @cao2025defi @bacry2015hawkes @hardiman2013endogeneity dự báo chỉ từ lịch sử sự kiện. Liệu vị thế _phân giải theo tầng ví_ (mất cân bằng, tập trung, đòn bẩy) có bổ sung sức mạnh dự báo so với tự kích thích hay không---vẫn chưa được kiểm định.

*G2 --- TPP thần kinh chưa được điều kiện hóa theo đông đúc ngoại sinh.* Các quá trình điểm hiện đại nhất @zuo2020thp @mei2017neuralhawkes @du2016rmtpp điều kiện hóa theo thời điểm và mark, không theo một luồng hiệp biến liên tục về vị thế thị trường---nên câu hỏi hiệp biến-đối-cường độ chưa được tách bạch _trong cùng một họ mô hình_.

*G3 --- Lây lan qua các giao thức mới chỉ được mô tả, chưa được dự báo.* @cao2025defi thiết lập cụm lây lan trên các giao thức trên mạng Blockchain khác nhau theo hướng mô tả; chưa công trình nào biến lan tỏa liên tài sản thành một dự báo _cảnh báo sớm_ có hiệu chỉnh, an toàn không rò rỉ, cho đợt bùng phát tiếp theo.

*G4 --- Chưa có cảnh báo sớm bùng phát đã hiệu chỉnh, nhận biết dịch chuyển.* Các phương pháp conformal @gibbs2021adaptive @zaffran2022adaptive đã tồn tại nhưng chưa được ghép nối với một quá trình điểm thanh lý để tạo ra các đảm bảo về độ trễ cảnh báo/tỷ lệ báo động giả có kiểm soát độ bao phủ dưới dịch chuyển chế độ thị trường.


*Đóng góp.* Luận văn này nhắm chính xác vào khoảng trống này: (C1) một bảng đông đúc phân giải theo tầng ví và nhãn bùng phát an toàn không rò rỉ, trên một kho dữ liệu on-chain 40,5 triệu sự kiện (@sec:related G1); (C2) một quá trình điểm thần kinh điều kiện hóa theo hiệp biến (CovTPP) tiêm đông đúc vào hàm nền cường độ $mu_k$ của @eq:intensity, tách bạch hiệu ứng hiệp biến trong cùng họ TPP thần kinh, đối chứng với mô hình nền THP (G2); (C3) các đặc trưng lan tỏa liên tài sản tường minh và một ST-GNN trên đồ thị vị thế, đối chứng với một Hawkes đa biến (G3); (C4) một đánh giá ưu tiên PR trên các khung ngoài mẫu giống hệt nhau, cùng một tầng hiệu chỉnh conformal thích nghi đã hoạch định cho dịch chuyển chế độ (G4, G5). Kết quả (@sec:results) xác nhận tuyên bố trung tâm của G1--G2: hiệp biến đông đúc gần như tăng gấp đôi PR-AUC so với các mô hình nền chỉ dựa vào cường độ, trong cùng một họ mô hình.

= Tổng quan Hệ thống <sec:system>

@fig:pipeline thể hiện luồng dữ liệu đầu-cuối, @fig:gates thể hiện hai cổng quyết định go/no-go đã định hình hướng đi, và @fig:models thể hiện bức tranh tổng thể các mô hình.

#figure(
  image("figs_vi/pipeline.pdf", width: 100%),
  caption: [Pipeline đầu-cuối. positions logs thô được tái tạo thành vị thế đã đóng, sau đó bộ xây dựng bảng tạo ra một dòng an toàn không rò rỉ cho mỗi (tài sản, khung 5 phút) trên một lưới thời gian toàn cục đồng bộ: đặc trưng lấy từ $[t-w,t]$, nhãn lấy từ cửa sổ tương lai rời rạc $(t,t+h]$. Bảng được chia theo thời gian và mọi mô hình được chấm điểm trên cùng các khung kiểm tra.],
) <fig:pipeline>

#figure(
  image("figs_vi/gates.pdf", width: 100%),
  caption: [Hai thử nghiệm khả thi định hình hướng đi _trước khi_ xây dựng bất kỳ mô hình nào. Thử nghiệm 1 (@sec:m0magnet) kiểm định giả thuyết nam châm thanh lý và bị bác bỏ. Thử nghiệm 2 (@sec:m0burst) xác nhận nhãn bùng phát dày đặc và có khả năng học mạnh.],
) <fig:gates>

#figure(
  image("figs_vi/models.pdf", width: 95%),
  caption: [Bức tranh tổng thể các mô hình. Ba mô hình nền quá trình điểm đã công bố chỉ tiêu thụ thời điểm sự kiện; ba mô hình trong luận văn này bổ sung 17 đặc trưng đông đúc/liên tài sản. Mũi tên nét đứt đánh dấu tương phản quyết định trong cùng một họ mô hình (THP → CovTPP). Cả sáu mô hình được chấm điểm trên cùng các khung kiểm tra ngoài mẫu (@tab:m2).],
) <fig:models>

== Tổng quan các Mô hình được Áp dụng <sec:modeloverview>

@fig:models nhóm sáu mô hình có tên gọi theo dữ liệu đầu vào: chỉ thời điểm sự kiện (ba mô hình nền quá trình điểm đã công bố) so với thời điểm sự kiện cộng véc-tơ hiệp biến đông đúc/liên tài sản 17 chiều (ba mô hình đề xuất trong luận văn này). Dưới đây là cơ chế của từng mô hình, bắt đầu từ quá trình Hawkes vì nó là nền tảng của mọi mô hình nền chỉ dựa vào cường độ, đồng thời là động lực trực tiếp cho hàm nền điều kiện hóa theo đông đúc trong @eq:intensity.


*Transformer Hawkes Process (THP).* THP thay hạt nhân mũ cố định bằng một hạt nhân đã học: một bộ mã hóa tự chú ý (self-attention) tiêu thụ chuỗi sự kiện quá khứ (và khoảng cách thời gian giữa các sự kiện) của từng tài sản, tạo ra một trạng thái ẩn $h_i$ cho mỗi sự kiện, từ đó đọc ra cường độ liên tục $lambda(t)="softplus"(v^top h_i + b + a(t-t_i))$. Mô hình này biểu đạt mạnh hơn hẳn hạt nhân mũ cổ điển, nhưng---giống các mô hình nền Hawkes---chỉ điều kiện hóa theo thời điểm sự kiện, không bao giờ theo trạng thái đông đúc.

*LightGBM (bộ phân loại hiệp biến).* Một tập hợp cây gradient boosting huấn luyện trực tiếp trên bảng 17 đặc trưng đông đúc để dự đoán nhãn nhị phân bùng phát @eq:burst, siêu tham số được tinh chỉnh bằng Optuna theo độ chính xác trung bình (average precision). Mô hình này không có khái niệm cường độ hay cấu trúc quá trình điểm; đây là mô hình nền phân biệt (discriminative) thuần túy mạnh nhất cho các hiệp biến.

*TPP thần kinh điều kiện hóa theo hiệp biến (CovTPP).* Phiên bản hiệp biến trực tiếp tương ứng với THP: một GRU chạy nhân quả trên chuỗi 17 đặc trưng (thay vì trên thời điểm sự kiện) để tạo trạng thái lịch sử $h_t$, đưa vào cùng đầu ra cường độ kiểu hazard $lambda_t="softplus"(w^top h_t+b)$, $P("bùng phát")=1-e^(-lambda_t)$. So sánh THP và CovTPP trong @tab:m2 tách bạch hiệu ứng của việc điều kiện hóa theo đông đúc, trong cùng một họ mô hình.

*GNN không gian--thời gian (ST-GNN).* Coi 40 tài sản là các nút trên lưới 5 phút toàn cục chung; một tầng đồ thị trao đổi một thông điệp thị trường liên tài sản giữa các nút đang hoạt động tại mỗi bước, và một GRU riêng cho từng nút mang trạng thái thời gian vào cùng đầu ra hazard như CovTPP. Mô hình này kiểm định liệu việc truyền thông điệp (message passing) tường minh có vượt qua các hiệp biến thị trường/lan tỏa đã thiết kế thủ công sẵn có trong bảng đặc trưng hay không.

= Tổng quan Dữ liệu <sec:data>

Nguồn dữ liệu chính là bộ sưu tập `logs` của cơ sở dữ liệu MongoDB `perpetuals_knowledge_graph`, ghi lại mọi sự kiện vòng đời mở/đóng cho các vị thế perpetual trên năm nền tảng (Hyperliquid, Jupiter, GMX-v2, APX, Myx) và năm blockchain. Các vị thế đã đóng được tái tạo và lưu tại `data/processed/positions.parquet`.

#figure(
  table(
    columns: (auto, auto, auto),
    align: (left, right, center),
    table.header([Đại lượng], [Giá trị], [Collection nguồn]),
    [Tổng số sự kiện log], [40.552.429], [`logs`],
    [Vị thế đã đóng], [1.342.059], [`closed_positions`],
    [Sự kiện thanh lý tường minh], [190.573], [`positions` (`Liquidate`)],
    [Tài sản có thanh lý], [249], [`positions`],
    [Điểm giá theo phút], [93.743.096], [`hyperliquid_prices`],
    [Vị thế đang mở (ảnh chụp)], [25.584], [`opening_positions`],
    [Kết quả backtest giao dịch], [567.784], [`trade_history`],
    [Độ dài dữ liệu], [491 ngày], [`logs`],
  ),
  caption: [Quy mô dữ liệu liên quan tới mô hình hóa bùng phát (số liệu đã kiểm chứng từ các collection).],
) <tab:scale>

*Mức độ sẵn có của các collection (đã kiểm chứng).* Có dữ liệu và hữu ích: `logs`, `closed_positions`, `opening_positions`, `hyperliquid_prices` (93,7 triệu điểm giá/phút), `hyperliquid_pairs`, `trade_history` (567 nghìn backtest), và các bảng trader đa tầm nhìn `web3_traders_{1D,3D,1W,1M}`. Không đủ hoặc thiếu: `signals` chỉ là một stub 29 văn bản, không giao nhau với ví perp; `market_stats` (108 văn bản) và ảnh chụp `aggregated_assets` quá thô để làm nguồn đông đúc biến đổi theo thời gian, nên đông đúc được tái tạo từ `logs` thay thế.

*Mức độ tập trung thanh lý.* Thanh lý tập trung ở các tài sản thanh khoản cao nhất: BTC (78.098), SOL (67.374), ETH (28.331), sau đó là một dải đuôi dài (XRP 2.173, BNB 1.223, DOGE 1.023, ...). Sự tập trung này định hình cả hai thử nghiệm khả thi bên dưới.

= Thử nghiệm Khả thi 1: Giả thuyết Nam châm Thanh lý (Bị Bác bỏ) <sec:m0magnet>

Trước khi cam kết theo hướng chính, chúng tôi kiểm định một ý tưởng lân cận hấp dẫn: rằng giá bị _hút_ về các cụm giá thanh lý dày đặc (hiệu ứng "nam châm" / stop-hunt). Giá thanh lý của mỗi vị thế mở được xấp xỉ bằng $"entry" times (1 minus.plus 1/"leverage")$ (Long $-$, Short $+$), trọng số theo quy mô, có hiệu lực trong khoảng $["open_ts", "close_ts")$; đường giá lấy từ `hyperliquid_prices`.

#figure(
  table(
    columns: (auto, auto, auto, auto),
    align: (left, right, right, center),
    table.header(
      [Tài sản], [Số vị thế], [Spearman($w$, lợi suất kỳ hạn)], [$p$ (Pearson)]
    ),
    [BTC], [399.044], [+0,017 / +0,029], [0,58 / 0,99],
    [SOL], [297.685], [+0,021], [0,97],
    [ETH], [201.350], [$-$0,001], [0,32],
  ),
  caption: [Thử nghiệm nam châm: kiểm định chiều hướng (Spearman giữa mất cân bằng vùng giá trọng số theo quy mô và lợi suất kỳ hạn) trên ba tài sản thanh khoản cao nhất. Tất cả đều null.],
) <tab:magnet>

Một kiểm định _hút_ sắc bén hơn---liệu giá có _chạm_ tới vùng giá trội gần nhất trong tầm dự báo nhiều hơn một mức gương cách đều ở phía đối diện---cũng cho kết quả null trên BTC: vùng giá bị chạm 2,4% / 6,0% số lần (tầm dự báo 120 / 360 phút) so với 2,7% / 6,1% cho mức gương ($z approx -0,66$ / $-0,22$). Tỷ lệ chạm đúng chiều về phía vùng giá là 0,496 / 0,509 (ngẫu nhiên 0,5), với khoảng tin cậy bootstrap 95% trải qua số 0.

*Kết luận.* Trên ba tài sản thanh khoản cao nhất (~900 nghìn vị thế) và hai dạng kiểm định độc lập, *không có tín hiệu nam châm thanh lý*. Cơ chế này không thể chứng minh được trên các tài sản chủ lực thanh khoản cao, nên bị *loại khỏi tuyên bố chính*. Bản đồ vùng giá thanh lý chỉ được giữ lại như một _đặc trưng_ ứng viên cho dự báo bùng phát. Lưu ý trung thực: giá thanh lý chỉ là xấp xỉ (không tính ký quỹ duy trì thực tế); các altcoin mỏng nhất thiếu mật độ dữ liệu để kiểm định nghiêm ngặt, nên tuyên bố chính xác là "không có nam châm trên các tài sản chủ lực thanh khoản cao."

= Thử nghiệm Khả thi 2: Nhãn Bùng phát (Vượt qua) <sec:m0burst>

Tiếp theo, chúng tôi kiểm chứng nhãn bùng phát @eq:burst: liệu nó có đủ cân bằng để huấn luyện, và liệu nó có thực sự dự đoán được hay không? Sự kiện thanh lý được gộp khung 5 phút theo từng tài sản (top-12 theo khối lượng thanh lý, gộp chung). Làm thước đo khả năng học, chúng tôi đo AUC của _một đặc trưng tầm thường duy nhất_---số lượt thanh lý trong 15 phút trước---khi dự đoán bùng phát tương lai.

#figure(
  table(
    columns: (auto, auto, auto, auto, auto),
    align: (right, right, right, right, right),
    table.header(
      [$h$ (phút)],
      [$theta$],
      [Tỷ lệ nền gộp],
      [Số dương],
      [AUC(15ph trước → bùng phát)],
    ),
    [5], [3], [0,0123], [17.029], [0,873],
    [5], [5], [0,0054], [7.522], [0,893],
    [15], [3], [*0,0377*], [*52.182*], [0,831],
    [15], [5], [0,0202], [27.994], [0,862],
    [60], [3], [0,1191], [164.938], [0,755],
    [60], [5], [*0,0785*], [*108.807*], [0,788],
  ),
  caption: [Tỷ lệ nền bùng phát và khả năng học theo tầm dự báo $h$ và ngưỡng $theta$. AUC dùng một đặc trưng cường độ trễ (proxy tự kích thích).],
) <tab:burstbase>

*Kết luận: vượt qua.* Tỷ lệ nền nằm trong khoảng huấn luyện được (1--12%) với số lượng dương lớn ($10^4$--$10^5$), và nhãn có *khả năng học mạnh*: chỉ một đặc trưng cường độ trễ đơn lẻ đã đạt AUC 0,75--0,91. Tự kích thích là hiện tượng thực và mạnh---tiền đề Hawkes của @eq:intensity được xác nhận bằng thực nghiệm. Đây là hình ảnh nghịch đảo của thất bại wallet-scoring (nhãn nhiễu $rho=0,013$). Chúng tôi khóa điểm vận hành chính tại $h=15$ phút, $theta=3$ (tỷ lệ nền 3,8%, 52.182 mẫu dương). *Quan trọng: vì một đặc trưng cường độ trễ tầm thường đã đạt AUC ≈0,87, đóng góp mô hình hóa phải được đo bằng _mức tăng so với mô hình nền tự kích thích này_, không phải bằng khả năng dự đoán thô.*

= Phương pháp: Bảng Đông đúc An toàn Không rò rỉ và các Mô hình Nền

== Bảng Đặc trưng

Dịch vụ `src/burst/panel_builder.py` xây dựng, với mỗi tài sản và khung 5 phút, một dòng gồm nhãn bùng phát @eq:burst và bốn nhóm đặc trưng (17 đặc trưng), tất cả tính từ thông tin sẵn có tại hoặc trước $t$:

- *Nền (tự kích thích):* `past_liq_short` (số lượt thanh lý trong 15 phút trước), `past_liq_long` (60 phút).
- *Đông đúc:* mất cân bằng long/short theo open interest; mất cân bằng theo tầng lớn và tầng nhỏ; độ bất đồng theo tầng (lớn $-$ nhỏ); tỷ trọng open interest của tầng lớn (mức tập trung); đòn bẩy trung bình của vị thế đang mở; tốc độ biến thiên open interest; tốc độ biến thiên cường độ thanh lý.
- *Khối lượng:* _giá trị danh nghĩa_ (USD) thanh lý của chính tài sản trong cửa sổ trễ 15 và 60 phút.
- *Liên tài sản (đa biến):* số lượt và giá trị danh nghĩa thanh lý trễ toàn thị trường, và _lan tỏa_ từ các tài sản khác. Đây là phiên bản rời rạc, thiết kế thủ công tương ứng với kích thích chéo-mark $alpha_(k'->k)$ trong @eq:intensity.

Open interest theo (chiều, tầng) được duy trì chính xác như một hàm bậc thang: mỗi vị thế đóng góp $+"quy mô"$ tại khung mở và $-"quy mô"$ tại khung đóng; tổng tích lũy cho trạng thái mở tại mọi khung. Để các đặc trưng liên tài sản được định nghĩa tốt, mọi bảng theo từng tài sản được đặt trên một lưới 5 phút _toàn cục, đồng bộ theo epoch_ duy nhất ($floor("ts"\/300)$). Các tầng ví là tam phân vị (tercile) theo quy mô, tính riêng cho từng tài sản (dựa trên quy mô, không dựa trên nhãn, nên an toàn không rò rỉ). Mọi đặc trưng dùng $[t-w, t]$; nhãn dùng $(t, t+h]$; hai cửa sổ này tách biệt nhau.

== Các Mô hình Nền

Chúng tôi đối chứng với các _phương pháp có tên gọi, đã công bố_, tất cả được huấn luyện trên giai đoạn huấn luyện và chấm điểm trên cùng khung kiểm tra và nhãn.

- *Hawkes đơn biến* (`src/burst/hawkes.py`): quá trình tự kích thích cổ điển với hạt nhân kích hoạt dạng mũ $g(tau)=alpha beta e^(-beta tau)$, huấn luyện riêng cho từng tài sản bằng hợp lý cực đại (theo khung nội sinh-crypto Hawkes của @bacry2015hawkes, @hardiman2013endogeneity). Điểm số theo từng khung là cường độ điều kiện $lambda(t)$.
- *Hawkes có thành phần thị trường:* tự kích thích cộng thêm một số hạng kích thích toàn thị trường với hệ số suy giảm chung---một phiên bản khả thi thay thế cho Hawkes đa biến xuyên-sàn của @cao2025defi.
- *Transformer Hawkes Process (THP)* (`src/burst/thp.py`): một quá trình điểm thời gian thần kinh @zuo2020thp với bộ mã hóa tự chú ý trên chuỗi sự kiện của từng tài sản và một cường độ liên tục $lambda(t)="softplus"(v^top h_i + b + a (t-t_i))$.

== Các mô hình đề xuất sử dụng hiệp biến

- *LightGBM* trên 17 đặc trưng, với siêu tham số được tinh chỉnh bằng Optuna (`src/burst/tuner.py`).
- *TPP thần kinh điều kiện hóa theo hiệp biến* (`src/burst/covtpp.py`): một GRU chạy nhân quả trên chuỗi khung 5 phút của 17 đặc trưng, cho trạng thái lịch sử $h_t$; cường độ bùng phát là $lambda_t="softplus"(w^top h_t + b)$ và hazard theo tầm dự báo là $P("bùng phát")=1-e^(-lambda_t)$. Đây là hiện thực hóa trực tiếp của cường độ điều kiện hóa theo hiệp biến trong @eq:intensity: _cùng_ họ quá trình điểm thần kinh như THP, nhưng điều kiện hóa theo hiệp biến đông đúc.
- *GNN không gian--thời gian* (`src/burst/stgnn.py`): 40 tài sản là các nút trên lưới toàn cục chung; một tầng đồ thị trộn đặc trưng với một thông điệp thị trường liên tài sản, và một GRU riêng cho từng nút mang trạng thái thời gian.

#figure(
  image("figs_vi/covtpp_stgnn_pipeline.pdf", width: 100%),
  caption: [Luồng dữ liệu nội bộ của hai mô hình hiệp biến thần kinh. Trên: CovTPP chạy một GRU nhân quả riêng cho từng tài sản trên chuỗi 17 đặc trưng (cộng khoảng cách log giữa khung), đọc hazard từ đầu ra Linear+softplus cuối cùng tại mỗi khung. Dưới: ST-GNN thay vào đó trộn đặc trưng của mọi tài sản hoạt động với một thông điệp trung bình thị trường liên tài sản _trước_ khi hồi quy, nên trạng thái thời gian tại mỗi nút đã mang thông tin liên tài sản ngay từ mỗi bước---đây chính là khác biệt kiến trúc mà @tab:m2 kiểm định so với các đặc trưng thị trường/lan tỏa thiết kế thủ công của LightGBM.],
) <fig:covtppstgnn>

Việc hiệu chỉnh đã hoạch định sẽ đối chứng conformal tĩnh với Suy luận Conformal Thích nghi @gibbs2021adaptive @zaffran2022adaptive; TPP điều kiện hóa theo hiệp biến là mục tiêu tự nhiên.

= Kết quả: Đông đúc có Vượt qua các Mô hình Nền Quá trình Điểm đã Công bố? <sec:results>

Chúng tôi xây dựng bảng trên toàn bộ 40 tài sản đạt ngưỡng thanh lý tối thiểu, thu được 4.239.195 dòng tài sản-khung với tỷ lệ bùng phát 1,22%. Bảng được chia _theo thời gian_ (không rò rỉ): 70% khung sớm nhất dùng huấn luyện (2.967.435 dòng, 1,51% dương), 30% khung muộn nhất dùng kiểm tra (1.271.760 dòng, 0,56% dương). Mọi mô hình trong @tab:m2 được chấm điểm trên cùng khung kiểm tra và nhãn.

#figure(
  table(
    columns: (auto, auto, auto, auto),
    align: (left, left, right, right),
    table.header([Mô hình], [Loại], [ROC-AUC ↑], [PR-AUC ↑]),
    table.cell(
      colspan: 4,
      align: left,
    )[_Mô hình nền quá trình điểm đã công bố (chỉ thời điểm sự kiện)_],
    [THP (TPP thần kinh; @zuo2020thp)], [cường độ], [0,9700], [0,1294],
    [Hawkes, +thị trường (đa biến), MLE], [cường độ], [0,9740], [0,1568],
    [Hawkes, đơn biến tự kích thích, MLE], [cường độ], [0,9746], [0,1570],
    table.cell(
      colspan: 4,
      align: left,
    )[_Mô hình dùng hiệp biến (luận văn này)_],
    [LGBM nền (cường độ trễ, 2 đặc trưng)], [phân biệt], [0,9078], [0,2281],
    [LGBM đầy đủ (+đông đúc+khối lượng+liên tài sản, đã chỉnh)],
    [phân biệt],
    [*0,9801*],
    [0,2502],
    [ST-GNN (đồ thị liên tài sản + GRU)],
    [không gian--thời gian],
    [0,9791],
    [0,2513],
    [*CovTPP (hazard GRU + hiệp biến)*], [TPP thần kinh], [0,9792], [*0,2556*],
    table.hline(),
    [Mức tăng của CovTPP so với Hawkes cổ điển (PR-AUC)], [], [], [+0,0986],
    [Mức tăng của CovTPP so với THP thần kinh (PR-AUC)], [], [], [+0,1262],
  ),
  caption: [Dự báo bùng phát ngoài mẫu trên giai đoạn kiểm tra muộn hơn, mọi mô hình chấm điểm trên cùng khung kiểm tra và nhãn (tỷ lệ nền 0,56%; PR-AUC ngẫu nhiên = 0,0056).],
) <tab:m2>

Năm quan sát, theo thứ tự độ tin cậy giảm dần:

+ *Mọi mô hình dùng hiệp biến đều vượt qua mọi mô hình nền quá trình điểm đã công bố trên precision-recall, với khoảng cách lớn.* Mô hình tốt nhất (TPP thần kinh điều kiện hóa theo hiệp biến) đạt PR-AUC 0,256 so với 0,157 của Hawkes cổ điển (+0,099) và 0,129 của THP thần kinh (+0,126). Đây là tuyên bố trung tâm của luận văn.
+ *Yếu tố quyết định là các hiệp biến, không phải họ mô hình---được chứng minh trong cùng một họ.* Quá trình điểm thần kinh tăng từ PR-AUC 0,129 (THP) lên 0,256 (CovTPP)---mức tăng khoảng 2 lần.
+ *ROC-AUC che giấu mất cân bằng; PR-AUC trung thực.* Mọi mô hình chỉ dựa vào cường độ đều dồn vào một dải hẹp, ROC-AUC ≈0,97 nhưng PR-AUC chỉ ≈0,13--0,16.
+ *Trong nhóm mô hình dùng hiệp biến, khác biệt là nhỏ.* CovTPP (0,2556), ST-GNN (0,2513), và LightGBM đã tinh chỉnh (0,2502) nằm trong khoảng ≈0,005 của nhau; Hawkes đa biến ngây thơ không thêm được gì (0,1568 so với 0,1570).
+ *Dịch chuyển phân phối hiện diện và là động lực cho hiệu chỉnh.* Tỷ lệ nền tập kiểm tra (0,56%) thấp hơn nhiều so với tập huấn luyện (1,51%).

Không có rò rỉ nhãn: biến dự báo dùng $[t-w,t]$ và nhãn dùng $(t,t+h]$; phép chia theo thời gian; tham số Hawkes và THP được ước lượng chỉ trên sự kiện thuộc giai đoạn huấn luyện.

= Độ bền vững: Walk-Forward Xoay vòng và Độ nhạy theo Chế độ Thị trường <sec:robustness>

@sec:results báo cáo một phép chia đơn theo thời gian 70/30: chỉ một lần rút mẫu từ một chế độ thị trường, đã được đánh dấu là hạn chế trong báo cáo M2 (NS1). Chúng tôi giải quyết trực tiếp vấn đề này. Bảng dữ liệu được chia lại thành walk-forward cửa sổ mở rộng---một cửa sổ huấn luyện ban đầu 40%, sau đó năm fold kiểm tra liên tiếp không chồng lấp (≈509 nghìn dòng mỗi fold)---để mô hình LightGBM nền và mô hình đầy đủ đã tinh chỉnh được khớp lại theo từng fold và chấm điểm ngoài mẫu năm lần thay vì một lần. Mỗi dòng kiểm tra được gắn nhãn thêm theo hai trục chế độ độc lập: một chế độ _ngoại sinh_ vĩ mô từ độ biến động thực hiện và xu hướng hàng ngày của BTC/ETH (lấy từ Binance Futures, chỉ dùng để gắn nhãn fold hậu kiểm, không bao giờ là đặc trưng của mô hình; độ biến động của altcoin/perp trong crypto phần lớn do beta vĩ mô chi phối bất kể sàn giao dịch, cùng logic với việc gắn nhãn chế độ bằng VIX), và một chế độ _nội sinh_ đông đúc từ tứ phân vị cường độ thanh lý toàn thị trường của chính bảng dữ liệu, bắt được các sự kiện đông đúc đơn-tài sản đặc thù mà nhãn vĩ mô không thấy được.

#figure(
  table(
    columns: (auto, auto, auto, auto, auto),
    align: (left, right, right, right, right),
    table.header(
      [Fold], [Dòng huấn luyện], [Dòng kiểm tra], [PR-AUC nền], [PR-AUC đầy đủ]
    ),
    [0], [1.695.645], [508.716], [0,4621], [0,5019],
    [1], [2.204.361], [508.716], [0,4227], [0,4628],
    [2], [2.713.077], [508.677], [0,3032], [0,3115],
    [3], [3.221.754], [508.733], [0,2364], [0,2492],
    [4], [3.730.487], [508.707], [0,2297], [0,2499],
    table.hline(),
    [Trung bình ± độ lệch chuẩn], [], [], [0,3308 ± 0,0955], [0,3551 ± 0,1071],
  ),
  caption: [Walk-forward xoay vòng, cửa sổ huấn luyện mở rộng, năm fold kiểm tra ngoài mẫu liên tiếp. PR-AUC giảm dần theo fold vì tỷ lệ dương trôi dạt giảm theo thời gian (nhất quán với dịch chuyển tỷ lệ nền huấn luyện/kiểm tra đã nêu ở @sec:results), không phải vì mô hình suy giảm: mức tăng ROC-AUC ổn định (bên dưới).],
) <tab:walkforward>

Mức tăng tự nó ổn định: ROC-AUC trung bình tăng từ 0,9283 ± 0,0198 (nền) lên 0,9821 ± 0,0025 (đầy đủ), mức tăng +0,0538 ± 0,0174; PR-AUC trung bình tăng từ 0,3308 ± 0,0955 lên 0,3551 ± 0,1071, mức tăng +0,0242 ± 0,0134. Mức tăng dương ở cả năm fold, nên không phải là hiện tượng giả tạo của phép chia đơn được báo cáo ở @tab:m2; độ lệch chuẩn của mức tăng ROC nhỏ so với trung bình của nó, trong khi của mức tăng PR thì không (độ lệch chuẩn ≈55% trung bình), nên _sự tồn tại_ của mức tăng được ủng hộ vững chắc nhưng độ lớn chính xác của nó vẫn mang phương sai giữa các phép chia mà con số phép chia đơn không thể hiện được.

#figure(
  table(
    columns: (auto, auto, auto, auto, auto, auto),
    align: (left, left, right, right, right, right),
    table.header(
      [Trục chế độ], [Nhóm], [n], [Tỷ lệ dương], [PR-AUC nền], [PR-AUC đầy đủ]
    ),
    [Biến động vĩ mô (BTC/ETH)],
    [biến động cao],
    [1.252.036],
    [0,98%],
    [0,3989],
    [0,4427],

    [], [biến động thấp], [1.291.513], [0,57%], [0,2608], [0,2869],
    [Xu hướng vĩ mô (BTC/ETH)],
    [giảm giá],
    [1.412.384],
    [0,86%],
    [0,3836],
    [0,4297],

    [], [tăng giá], [1.131.165], [0,65%], [0,2813], [0,3074],
    [Đông đúc nội sinh], [đông đúc cao], [933.894], [1,44%], [0,4367], [0,4798],
    [], [đông đúc vừa], [852.622], [0,47%], [0,1243], [0,1456],
    [], [đông đúc thấp], [757.033], [0,28%], [0,0497], [0,0757],
  ),
  caption: [Mức tăng đông đúc phân theo chế độ thị trường, trên các dự đoán ngoài mẫu gộp từ @tab:walkforward. Mức tăng tồn tại ở mọi nhóm trên cả hai trục chế độ; lớn nhất chính xác ở nơi mô hình nền tự kích thích yếu nhất (thị trường giảm giá/biến động cao, giai đoạn đông đúc thấp).],
) <tab:regime>

Hai phát hiện nổi bật. Thứ nhất, mức tăng nhạy theo chế độ nhưng không bao giờ biến mất: nó gần như gấp đôi ở chế độ biến động cao và giảm giá (+0,044 và +0,046 PR-AUC) so với chế độ biến động thấp và tăng giá (+0,026 mỗi loại)---các hiệp biến đông đúc quan trọng nhất chính xác khi thị trường căng thẳng, đây là chế độ có ý nghĩa vận hành nhất đối với một hệ thống cảnh báo sớm. Thứ hai, chế độ đông đúc nội sinh là ranh giới sắc nét hơn: trong giai đoạn đông đúc thấp, mô hình nền cường độ trễ gần như không tốt hơn ngẫu nhiên (ROC-AUC 0,7958, PR-AUC 0,0497 so với tỷ lệ nền 0,28%), trong khi mô hình đầy đủ khôi phục lại phần lớn khả năng phân biệt (ROC-AUC 0,9711); các đặc trưng đông đúc phát huy tác dụng mạnh nhất chính xác ở nơi tự kích thích một mình bó tay.

Cuối cùng, chúng tôi kiểm tra độ bền của mô hình đầy đủ trực tiếp trên năm cụm bùng phát thanh lý đồng thời lớn nhất trong dữ liệu (năm khung 5 phút hàng đầu theo số lượng bùng phát liên tài sản, mỗi khung được đánh giá trong cửa sổ ±6 giờ quanh cụm, không chồng lấp). Mô hình giữ ROC-AUC 0,968--0,987 và độ chính xác tại top-5% từ 0,23 đến 0,83 trên cả năm cụm, với độ nhớ tại top-5% là 0,69--0,81---bằng chứng cho thấy mức tăng đo trên các độ đo trung bình theo fold không che giấu một lần bỏ sót ở những vụ sụp đổ có ý nghĩa vận hành thực sự.

== Nghiên cứu Trường hợp có Tên: Sự kiện Thanh lý Ngày 10--11/10/2025 <sec:oct2025>

Mọi fold và nhóm chế độ ở trên đều ẩn danh theo thiết kế. Để đối chiếu mô hình với một sự kiện thực, có thể kiểm chứng độc lập, chúng tôi xác định ngày có số khung bùng phát cao thứ hai trong toàn bộ 491 ngày của tập dữ liệu: ngày 10/10/2025 (559 khung bùng phát trên 38 tài sản hoạt động, do BTC, SOL, và ETH chi phối), trùng khớp với vụ sụp đổ crypto ngày 10--11/10/2025 được báo chí ghi nhận rộng rãi---một đợt bán tháo do cú sốc thuế quan gây ra, được xem là sự kiện thanh lý đồng thời lớn nhất trong lịch sử thị trường (khoảng 19 tỷ USD bị thanh lý trên toàn ngành), với các tài sản lớn được báo cáo chịu ảnh hưởng nặng nhất---khớp với những gì bảng dữ liệu của chúng tôi cho thấy một cách độc lập.

Ngày này nằm trong cửa sổ huấn luyện ban đầu 40% của walk-forward (@sec:robustness), nên chưa từng được chấm điểm ngoài mẫu. Chúng tôi huấn luyện lại BASELINE và FULL chỉ trên dữ liệu trước ngày 7/10/2025 và đánh giá trên cửa sổ 9--14/10/2025 (54.968 dòng tài sản-khung, tỷ lệ dương 3,31%---cao hơn một bậc độ lớn so với trung bình toàn bảng, phù hợp với một đợt sụp đổ dây chuyền). Mô hình đầy đủ đạt ROC-AUC 0,9694 / PR-AUC 0,6982 so với 0,9626 / 0,6917 của mô hình nền (mức tăng +0,0068 / +0,0065, nhỏ hơn mức tăng trung bình toàn bảng vì mô hình nền cường độ trễ đã mạnh sẵn một khi đợt sụp đổ dây chuyền đang diễn ra), và độ chính xác tại top-5% là 0,51 với độ nhớ tại top-5% là 0,77.

#figure(
  image(
    "../pipeline/outputs/b07_oct2025_case_study/oct2025_timeline.png",
    width: 92%,
  ),
  caption: [P(bùng phát) dự đoán cho BTC xuyên suốt sự kiện ngày 10--11/10/2025 (890 khung bùng phát trong cửa sổ), mô hình chỉ được huấn luyện trên dữ liệu trước ngày 7/10/2025. Đường đỏ đánh dấu khung bùng phát thực tế; đường đứt nét là ngưỡng cảnh báo (điểm số top-5% của tập huấn luyện). Cảnh báo đầu tiên của mô hình trên BTC đến trước khung bùng phát thực tế đầu tiên 20 phút.],
) <fig:oct2025>

Với ngưỡng cảnh báo hiệu chỉnh từ điểm số top-5% của chính tập huấn luyện, cảnh báo đầu tiên của mô hình trên BTC đến trước khung bùng phát thực tế đầu tiên 20 phút---hơn một khung thời gian dự báo 15 phút thời gian cảnh báo sớm trên sự kiện thanh lý lớn nhất trong cửa sổ dữ liệu, với một mô hình chưa từng thấy sự kiện này trong quá trình huấn luyện.

== Mở rộng Walk-Forward cho CovTPP và ST-GNN <sec:covtppstgnnwf>

Phần còn lại của NS1 là thứ hạng ba chiều ở @tab:m2 giữa CovTPP, ST-GNN, và LightGBM đã tinh chỉnh, vốn chỉ dựa trên một phép chia đơn (cách nhau ≈0,005 PR-AUC). Chúng tôi chạy lại đúng walk-forward năm fold cửa sổ mở rộng và các nhãn chế độ của @sec:robustness cho CovTPP và ST-GNN (walk-forward của LightGBM đã được báo cáo ở đó).

#figure(
  table(
    columns: (auto, auto, auto),
    align: (left, right, right),
    table.header([Mô hình], [ROC-AUC trung bình], [PR-AUC trung bình]),
    [CovTPP], [0,9822 ± 0,0023], [0,3647 ± 0,0991],
    [ST-GNN], [0,9820 ± 0,0022], [0,3631 ± 0,1011],
  ),
  caption: [CovTPP so với ST-GNN, trung bình ± độ lệch chuẩn trên cùng năm fold walk-forward như @tab:walkforward. Hai mô hình bám sát nhau trong phạm vi một độ lệch chuẩn của chính fold đó tại mọi fold và mọi nhóm chế độ (chế độ biến động, xu hướng, và đông đúc đều chênh lệch ≤0,002 PR-AUC giữa hai mô hình) --- ví dụ chế độ đông đúc: high\_crowd 0,4919 (CovTPP) so với 0,4902 (ST-GNN); low\_crowd 0,0869 so với 0,0770.],
) <tab:covtppstgnnwf>

#figure(
  image(
    "../pipeline/outputs/b08_covtpp_stgnn_walkforward/covtpp_stgnn_walkforward.png",
    width: 78%,
  ),
  caption: [PR-AUC theo fold, CovTPP so với ST-GNN, qua cùng năm fold walk-forward như @fig:m6. Hai đường gần như trùng khít nhau ở mọi fold.],
) <fig:covtppstgnnwf>

Walk-forward xác nhận, chứ không lật ngược, phát hiện trên phép chia đơn của @sec:results: việc truyền thông điệp đồ thị liên tài sản tường minh (ST-GNN) không vượt qua một cách đáng tin cậy việc điều kiện hóa GRU theo từng tài sản trên cùng hiệp biến đông đúc (CovTPP) tại bất kỳ điểm nào trong năm fold hay sáu nhóm chế độ. Điều này giải quyết NS1: cả ba mô hình dùng hiệp biến---LightGBM, CovTPP, ST-GNN---nay đều có khoảng tin cậy walk-forward, và tuyên bố về thứ hạng vững chắc không đổi: mô hình điều kiện hóa theo hiệp biến vượt qua mô hình nền chỉ dựa vào cường độ với khoảng cách lớn, ổn định; thứ hạng _giữa_ ba mô hình dùng hiệp biến vẫn không thể phân biệt được về mặt thống kê, không phải chỉ "còn tạm thời chờ thêm fold".

== Độ đo Vận hành: Hiệu chỉnh, Tải Cảnh báo, Thời gian Cảnh báo sớm, và Giá trị Kinh tế <sec:opmetrics>

PR-AUC và ROC-AUC tóm tắt chất lượng xếp hạng nhưng không trả lời câu hỏi nào mà một quyết định triển khai thực sự cần (NS2): điểm số có phải là xác suất đáng tin cậy không, một quy tắc quyết định cố định bắn ra bao nhiêu cảnh báo giả mỗi ngày, một cảnh báo cho bao nhiêu thời gian trước khi đợt sụp đổ dây chuyền bắt đầu, và mô hình có bắt được các đợt sụp đổ mang nhiều đô-la rủi ro nhất hay không---chứ không chỉ nhiều khung nhất. Chúng tôi trả lời cả bốn câu hỏi từ các dự đoán ngoài mẫu gộp của mô hình LightGBM đầy đủ qua năm fold walk-forward của @sec:robustness (2.543.549 dòng, 227,6 ngày, `pipeline/b09_operational_metrics.py`).

*Hiệu chỉnh.* @fig:reliability vẽ $P("bùng phát")$ dự đoán so với tần suất bùng phát quan sát được trong mười khoảng đều nhau. Sai số Hiệu chỉnh Kỳ vọng (ECE) là 0,0533, và đường cong nằm hẳn dưới đường chéo ở mọi khoảng trên 0,1: mô hình *quá tự tin*---dự đoán 0,8 tương ứng với tỷ lệ quan sát gần 0,1--0,3 hơn. Điểm số thô là một bộ xếp hạng tốt (như @tab:m2/@tab:walkforward đã cho thấy) nhưng chưa phải xác suất dùng được; bất kỳ ứng dụng định cỡ vị thế hay điều chỉnh ký quỹ nào (@sec:related) đều cần một tầng hiệu chỉnh lại (Platt scaling hoặc isotonic regression) trước khi triển khai, không chỉ riêng mô hình xếp hạng.

#figure(
  image("../pipeline/outputs/b09_operational_metrics/reliability_diagram.png", width: 55%),
  caption: [Biểu đồ độ tin cậy, mô hình LightGBM đầy đủ, dự đoán ngoài mẫu walk-forward gộp, 10 khoảng đều nhau. ECE = 0,0533; đường cong dưới đường chéo cho thấy sự quá tự tin có hệ thống.],
) <fig:reliability>

*Tải cảnh báo tại một điểm vận hành cố định.* Cố định recall ở 80% (ngưỡng chọn hậu kiểm trên tập OOF gộp để báo cáo, không phải ngưỡng sản xuất) cho độ chính xác 0,179 và 315,2 cảnh báo giả/ngày gộp trên 39 tài sản---8,08 cảnh báo giả mỗi tài sản mỗi ngày, khoảng một lần mỗi ba giờ. Đây là con số một sản phẩm cảnh báo thực sự phải dự trù: điểm vận hành recall 80% chỉ khả dụng nếu tự động hóa hạ nguồn (giảm đòn bẩy, thoát vault) có thể chịu được một cảnh báo khoảng mỗi 3 giờ mỗi tài sản mà không tốn kém quá mức.

*Thời gian cảnh báo sớm.* Chúng tôi gộp các khung bùng phát liên tiếp/gần nhau theo từng tài sản thành các "sự kiện" sụp đổ rời rạc (tổng 4.283 sự kiện) và, với mỗi sự kiện, đo thời gian từ _lúc bắt đầu_ của đợt cảnh báo trước đó (không chỉ khung cảnh báo gần nhất, vốn sẽ đánh giá thấp thời gian cảnh báo khi mô hình đã cảnh báo liên tục) đến thời điểm bắt đầu sự kiện. 98,6% sự kiện (4.225/4.283) nhận được ít nhất một cảnh báo tại hoặc trước khi bắt đầu; thời gian cảnh báo sớm trung vị là *90 phút*, với p10 = 10 phút và p90 = 570 phút (@fig:leadtime). Một đuôi nhỏ (64 sự kiện, 1,5%) có thời gian cảnh báo sớm trên 48 giờ---mô hình nằm liên tục ở trạng thái cảnh báo trên một tài sản đông đúc dai dẳng chứ không phải một cảnh báo rời rạc, đó là lý do trung bình (962,5 phút) không phải con số đại diện; trung vị và p90 mới là con số vận hành thực sự. Chỉ 4,0% sự kiện được cảnh báo (171/4.225) nhận cảnh báo đầu tiên tại hoặc sau khi bắt đầu (bắt kịp cùng khung hoặc muộn). Thời gian cảnh báo sớm trung vị 90 phút gấp sáu lần khung dự báo 15 phút---đủ thời gian thực để hành động phòng vệ trên chuỗi, không chỉ là một tín hiệu nhấp nháy trên dashboard.

#figure(
  image("../pipeline/outputs/b09_operational_metrics/lead_time_distribution.png", width: 68%),
  caption: [Phân phối thời gian cảnh báo sớm qua 4.225 sự kiện sụp đổ được cảnh báo (cắt tại 48h; 64 sự kiện vượt ngưỡng này là trạng thái cảnh báo liên tục, không phải cảnh báo rời rạc). Trung vị 90 phút, p10 10 phút, p90 570 phút.],
) <fig:leadtime>

*Giá trị kinh tế (theo trọng số notional).* Nhãn ($theta gt.eq 3$ thanh lý trong 15 phút) coi một cụm ba lần thanh lý bán lẻ nhỏ giống hệt như khởi đầu một đợt sụp đổ dây chuyền chín chữ số. Đặt trọng số average precision theo $log(1 + "notional USD tương lai")$ cho các khung dương (đặt trọng số theo đô-la thô sẽ để một đợt sụp đổ lớn nhất, 39,5 triệu USD, chi phối toàn bộ đường cong nên không được dùng) cho economic PR-AUC 0,8321, so với 0,3873 không trọng số trên cùng dự đoán---mô hình xếp hạng các đợt sụp đổ notional lớn đáng tin cậy hơn nhiều so với các đợt nhỏ. Tại điểm vận hành recall 80%, notional recall (tỷ lệ giá trị thanh lý USD tương lai bắt được) là *0,879*, cao hơn count recall 0,800: mô hình ưu tiên bắt được các đợt sụp đổ mang nhiều đô-la rủi ro hơn, không chỉ nhiều khung hơn.

= Thảo luận

Kết quả xác nhận hướng đi và định vị chính xác vấn đề mở. Bùng phát có thể dự đoán được, tự kích thích chi phối tín hiệu dễ, và mọi mô hình dùng hiệp biến đều vượt qua các mô hình nền chỉ dựa vào cường độ đã công bố trên độ đo trung thực, với TPP điều kiện hóa theo hiệp biến là tốt nhất. Bằng chứng rõ ràng nhất là tương phản _trong cùng một họ_: quá trình điểm thần kinh gần như tăng gấp đôi PR-AUC (0,129→0,256) khi cường độ của nó được điều kiện hóa theo hiệp biến đông đúc thay vì chỉ theo thời điểm sự kiện, tách bạch đông đúc---không phải lựa chọn bộ học---là nguồn gốc của khả năng dự đoán vượt ra ngoài tự kích thích. Phát hiện phương pháp luận trung tâm là sự _phân kỳ ROC/PR_ đi kèm: Hawkes cổ điển, Hawkes đa biến, và THP thần kinh đều đạt ROC-AUC ≈0,97 nhưng PR-AUC chỉ ≈0,13--0,16. Nhất quán với điều này, việc bổ sung một đồ thị liên tài sản tường minh (ST-GNN) không vượt qua bộ phân loại, vì các đặc trưng thị trường/lan tỏa thiết kế thủ công đã mã hóa sẵn tín hiệu liên tài sản.

Kết quả null của nam châm (@sec:m0magnet) là một kết quả tiêu cực hữu ích: nó ngăn việc xây dựng trên một hiệu ứng mà dữ liệu không ủng hộ, và giữ cho luận văn trung thực về những gì vùng giá thanh lý thực sự làm.

@sec:robustness cung cấp chính khoảng tin cậy walk-forward mà đoạn trên yêu cầu, cho phép so sánh LightGBM nền/đầy đủ: mức tăng giữ vững qua năm fold cửa sổ mở rộng và qua mọi nhóm của hai trục chế độ độc lập, và lớn nhất ở các giai đoạn căng thẳng (giảm giá, biến động cao) và đông đúc thấp---chính là các chế độ mà một hệ thống cảnh báo sớm cần phục vụ.

= Hạn chế

+ *Mô hình gọn nhẹ.* Mọi mô hình thần kinh đều được thiết kế nhỏ có chủ đích: THP (32 chiều, 2 tầng, 3 epoch, ngữ cảnh 64 sự kiện), TPP hiệp biến và ST-GNN (GRU 1 tầng, 48--64 ẩn, ≤4 epoch), Hawkes cổ điển dùng hạt nhân mũ với $beta$ trên một lưới nhỏ (MLE Nelder--Mead).
+ *Khác biệt nhỏ giữa các mô hình dùng hiệp biến---đã được xác nhận, không chỉ nghi ngờ, bằng walk-forward.* CovTPP, ST-GNN, và bộ phân loại đã tinh chỉnh khác nhau ≤0,005 PR-AUC trên phép chia đơn ở @tab:m2; @sec:covtppstgnnwf cho thấy điều này giữ vững qua năm fold walk-forward và sáu nhóm chế độ (CovTPP và ST-GNN bám sát nhau trong phạm vi ≤0,002 PR-AUC ở mọi nơi được kiểm tra). Tuyên bố rằng một mô hình dùng hiệp biến nào đó là _tốt nhất_ không còn là tạm thời mà thực sự không được bằng chứng ủng hộ; tuyên bố vững chắc là mô hình điều kiện hóa theo hiệp biến ≫ mô hình chỉ dựa vào cường độ, không phải thứ hạng giữa CovTPP/ST-GNN/LightGBM.
+ *Chế độ vĩ mô là proxy thị trường ngoại sinh, không đặc thù theo tài sản.* Nhãn biến động/xu hướng BTC/ETH là proxy hợp lý cho beta crypto trên các tài sản lớn nhưng có thể gắn nhãn sai cho các đợt bùng phát đặc thù trên tài sản mỏng/meme (ví dụ `kBONK`, `FARTCOIN`, `PENGU`) tách rời khỏi chu kỳ vĩ mô; chế độ đông đúc nội sinh bù đắp một phần nhưng bản thân nó cũng suy ra từ cường độ thanh lý tổng hợp, không phải cú sốc theo từng tài sản.
+ *Liên tài sản qua đặc trưng thiết kế thủ công, không phải một quá trình đã khớp mô hình.*
+ *Giá thanh lý xấp xỉ* (không tính ký quỹ duy trì thực tế, không tính ký quỹ chéo).
+ *Không có hiệp biến tỷ lệ tài trợ* (vắng mặt trong schema); chỉ có thể dùng chu kỳ tài trợ.
+ *Điểm số thô quá tự tin, chưa sẵn sàng triển khai như một xác suất.* ECE 0,0533 với đường cong độ tin cậy nằm dưới đường chéo (@sec:opmetrics): mô hình phóng đại $P("bùng phát")$ ở mọi mức độ tin cậy trên 0,1. Xếp hạng (PR-AUC/ROC-AUC, mọi kết quả walk-forward và kiểm tra độ bền trên sự kiện) không bị ảnh hưởng, nhưng bất kỳ việc dùng điểm số thô như xác suất---định cỡ vị thế, ký quỹ động, cảnh báo có kiểm soát độ phủ---đều cần một tầng hiệu chỉnh lại trước.
+ *Tải cảnh báo và điểm vận hành recall 80% là ước lượng một điểm, chưa quét toàn dải.* @sec:opmetrics cố định recall ở 80% như một điểm vận hành minh họa (8,08 cảnh báo giả/ngày/tài sản, thời gian cảnh báo sớm trung vị 90 phút); cần một phép quét đầy đủ precision-recall theo ngân sách cảnh báo, và tỷ lệ cảnh báo giả theo từng tài sản (thay vì gộp), trước khi định cỡ ngân sách cảnh báo cho một hệ thống sản xuất cụ thể.

= Tóm tắt Phát hiện Chính

*F1:* Hiệu ứng nam châm bị bác bỏ. Không có hiện tượng giá bị hút về vùng giá thanh lý trên BTC/SOL/ETH dưới hai dạng kiểm định.

*F2:* Nhãn bùng phát dày đặc và có khả năng học mạnh. Tỷ lệ nền 1--12% với $10^4$--$10^5$ mẫu dương; một đặc trưng cường độ trễ đơn lẻ cho AUC 0,75--0,91. Điểm vận hành đã khóa: $h=15$ phút, $theta=3$.

*F3:* Mô hình dùng hiệp biến vượt qua mô hình nền quá trình điểm đã công bố trên PR-AUC. PR-AUC 0,256 (CovTPP) > 0,251 (ST-GNN) > 0,250 (tuned LightGBM) ≫ 0,157 (Hawkes cổ điển) và 0,129 (THP thần kinh).

*F4:* Hiệp biến, không phải loại mô hình, là động lực của mức tăng. Cùng một họ TPP thần kinh tăng gấp đôi PR-AUC (0,129→0,256) khi được điều kiện hóa theo hiệp biến đông đúc.

*F5:* Nhãn đáng tin cậy, khác với wallet skill. Nhãn bùng phát dạng đếm sự kiện ($rho$ ≫ 0) tránh được nhiễu $rho=0,013$ từng giới hạn công thức trước đây.

*F6:* Mức tăng đông đúc của LightGBM giữ vững qua walk-forward xoay vòng năm fold (mức tăng PR-AUC +0,0242 ± 0,0134, mức tăng ROC-AUC +0,0538 ± 0,0174, dương ở mọi fold) và mọi nhóm của hai trục chế độ độc lập (@sec:robustness), lớn nhất ở các chế độ căng thẳng và đông đúc thấp---chính xác là nơi một hệ thống cảnh báo sớm cần hoạt động tốt.

*F7:* CovTPP và ST-GNN bám sát nhau trong phạm vi ≤0,002 PR-AUC qua cùng năm fold và sáu nhóm chế độ (@sec:covtppstgnnwf): thứ hạng ba chiều trên phép chia đơn ở @tab:m2 không phải thứ hạng đáng tin cậy, chỉ có mô hình điều kiện hóa theo hiệp biến ≫ mô hình chỉ dựa vào cường độ là đáng tin.

*F8:* Thời gian cảnh báo sớm trung vị 90 phút (gấp sáu lần khung dự báo 15 phút) tại điểm vận hành recall 80% cố định, và mô hình bắt được tỷ lệ notional USD tương lai (0,879) cao hơn tỷ lệ số lượng sự kiện thô (0,800)---nhưng điểm số thô *quá tự tin* (ECE 0,0533) và cần hiệu chỉnh lại trước khi dùng ngoài mục đích xếp hạng (@sec:opmetrics).

= Bước Tiếp theo

*NS1 (đã giải quyết, @sec:robustness, @sec:covtppstgnnwf):* Walk-forward đa fold xoay vòng nay bao phủ cả ba mô hình dùng hiệp biến (LightGBM, CovTPP, ST-GNN), kèm độ nhạy theo chế độ vĩ mô (BTC/ETH) và chế độ đông đúc nội sinh. Kết quả: mức tăng đông đúc của LightGBM vững chắc qua các fold và chế độ; thứ hạng ba chiều giữa các mô hình dùng hiệp biến không thể phân biệt được với nhiễu phép chia và không nên báo cáo như một thứ hạng.

*NS2 (đã giải quyết, @sec:opmetrics):* Độ đo tại điểm vận hành tính tại recall 80% cố định: độ chính xác 0,179, 8,08 cảnh báo giả/ngày/tài sản, thời gian cảnh báo sớm trung vị 90 phút (ví dụ +20 phút trên BTC ở @sec:oct2025 là một điểm trong phân phối này), ECE 0,0533 (quá tự tin, cần hiệu chỉnh lại trước khi dùng để định cỡ vị thế), và economic PR-AUC 0,8321 so với 0,3873 không trọng số. Còn lại: PR-AUC có điều kiện theo open interest không tầm thường chưa được tính.

*NS3:* Hiệu chỉnh conformal thích nghi qua dịch chuyển chế độ (tỷ lệ nền kiểm tra 0,56% so với huấn luyện 1,51%).

*NS4:* Hiệu chỉnh TPP điều kiện hóa theo hiệp biến (@sec:results), và khớp một Hawkes có mark/đa biến để diễn giải kích thích $alpha_(k'->k)$; kiểm tra độ bền của khoảng cách với mô hình nền bằng một TPP thần kinh mạnh hơn.

= Hình ảnh

#figure(
  image(
    "../pipeline/outputs/b01_burst_baseline/burst_baseline_lift.png",
    width: 92%,
  ),
  caption: [Dự báo bùng phát trên giai đoạn kiểm tra theo thời gian, an toàn không rò rỉ. Trái: ROC-AUC và PR-AUC ngoài mẫu cho mô hình nền LightGBM tự kích thích so với mô hình đầy đủ đã tinh chỉnh. Phải: mức độ quan trọng của đặc trưng LightGBM của mô hình đầy đủ. Xem @tab:m2 để so sánh đầy đủ.],
) <fig:m1>

#figure(
  image(
    "../pipeline/outputs/b06_regime_robustness/regime_robustness.png",
    width: 92%,
  ),
  caption: [Walk-forward xoay vòng và độ bền theo chế độ thị trường (@sec:robustness). Trái: PR-AUC theo fold cho mô hình nền và mô hình đầy đủ LightGBM qua năm fold cửa sổ mở rộng của @tab:walkforward. Phải: mức tăng PR-AUC (đầy đủ − nền) theo chế độ đông đúc nội sinh, từ @tab:regime.],
) <fig:m6>

*Báo cáo hỗ trợ.* Các báo cáo thử nghiệm chi tiết tại `m0-magnet-findings.md`, `m0-burst-findings.md`, `m1-crowding-lift-findings.md`, `m2-baselines-findings.md`. Trích dẫn công trình liên quan (@sec:related to @sec:gap) được liệt kê dưới đây; các mục được đánh dấu _[unverified]_ trong `references.bib` đã xác nhận tiêu đề/mã arXiv nhưng cần kiểm tra tác giả/nơi công bố trước bản nộp cuối cùng.

#bibliography("references.bib", style: "ieee", title: "Tài liệu tham khảo")
